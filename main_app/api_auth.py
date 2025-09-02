"""
API Authentication and Authorization for Trading Pro
Handles API key authentication, rate limiting, and access control
"""

import time
import hashlib
import hmac
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import APISubscriber, APIAccessLog


def get_client_ip(request):
    """Get the client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_api_access(subscriber, request_type, endpoint, method, ip_address, 
                   user_agent, request_data, response_status, response_data, processing_time_ms=None):
    """Log API access for monitoring and debugging"""
    try:
        APIAccessLog.objects.create(
            subscriber=subscriber,
            request_type=request_type,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            request_data=request_data,
            response_status=response_status,
            response_data=response_data,
            processing_time_ms=processing_time_ms
        )
    except Exception as e:
        # Log error but don't fail the request
        print(f"Failed to log API access: {e}")


def api_key_required(view_func):
    """
    Decorator to require API key authentication
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        
        # Get API key from header
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return JsonResponse({
                'error': 'API key required',
                'message': 'Please provide X-API-Key header'
            }, status=401)
        
        # Find subscriber by API key
        try:
            subscriber = APISubscriber.objects.get(api_key=api_key)
        except APISubscriber.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }, status=401)
        
        # Check if subscriber is active
        if subscriber.status != 'active':
            return JsonResponse({
                'error': 'Account not active',
                'message': f'Account status: {subscriber.status}'
            }, status=403)
        
        # Check rate limiting
        if subscriber.is_rate_limited():
            log_api_access(
                subscriber=subscriber,
                request_type='rate_limit',
                endpoint=request.path,
                method=request.method,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_data={},
                response_status=429,
                response_data={'error': 'Rate limit exceeded'}
            )
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Maximum {subscriber.rate_limit_per_hour} requests per hour allowed'
            }, status=429)
        
        # Add subscriber to request for use in view
        request.api_subscriber = subscriber
        
        # Process the request
        response = view_func(request, *args, **kwargs)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Increment request count
        subscriber.increment_request_count()
        
        # Log the access
        log_api_access(
            subscriber=subscriber,
            request_type='signal',
            endpoint=request.path,
            method=request.method,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_data=getattr(request, 'data', {}),
            response_status=response.status_code,
            response_data=getattr(response, 'data', {}),
            processing_time_ms=processing_time_ms
        )
        
        return response
    
    return wrapper


def webhook_signature_required(view_func):
    """
    Decorator to verify webhook signature
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Get signature from header
        signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE')
        if not signature:
            return JsonResponse({
                'error': 'Webhook signature required',
                'message': 'Please provide X-Webhook-Signature header'
            }, status=401)
        
        # Get subscriber from API key
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return JsonResponse({
                'error': 'API key required',
                'message': 'Please provide X-API-Key header'
            }, status=401)
        
        try:
            subscriber = APISubscriber.objects.get(api_key=api_key)
        except APISubscriber.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }, status=401)
        
        # Verify signature
        expected_signature = hmac.new(
            subscriber.secret_key.encode('utf-8'),
            request.body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return JsonResponse({
                'error': 'Invalid signature',
                'message': 'Webhook signature verification failed'
            }, status=401)
        
        request.api_subscriber = subscriber
        return view_func(request, *args, **kwargs)
    
    return wrapper


def generate_webhook_signature(secret_key, payload):
    """Generate webhook signature for outgoing requests"""
    return hmac.new(
        secret_key.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()


class APIRateLimitMiddleware:
    """
    Middleware to handle rate limiting at the application level
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only apply to API endpoints
        if not request.path.startswith('/api/v1/'):
            return self.get_response(request)
        
        # Get API key
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return self.get_response(request)
        
        # Check cache for rate limiting
        cache_key = f"api_rate_limit:{api_key}"
        current_requests = cache.get(cache_key, 0)
        
        # Get subscriber to check rate limit
        try:
            subscriber = APISubscriber.objects.get(api_key=api_key)
            if current_requests >= subscriber.rate_limit_per_hour:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {subscriber.rate_limit_per_hour} requests per hour allowed'
                }, status=429)
        except APISubscriber.DoesNotExist:
            pass
        
        # Increment counter
        cache.set(cache_key, current_requests + 1, 3600)  # 1 hour
        
        response = self.get_response(request)
        return response


