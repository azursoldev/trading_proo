"""
REST API Views for External Systems
Provides trading signals and market data to external subscribers
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import TradingSignal, APISubscriber, SignalDelivery
from .api_auth import api_key_required, webhook_signature_required
from .signal_service import SignalGenerator


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(api_key_required, name='dispatch')
class TradingSignalsAPIView(View):
    """
    API endpoint for external systems to retrieve trading signals
    """
    
    def get(self, request):
        """Get trading signals based on subscriber preferences"""
        subscriber = request.api_subscriber
        
        # Build query based on subscriber preferences
        query = Q()
        
        # Filter by subscribed tickers
        if subscriber.subscribed_tickers:
            query &= Q(ticker__symbol__in=subscriber.subscribed_tickers)
        
        # Filter by minimum confidence threshold
        query &= Q(confidence__gte=subscriber.min_confidence_threshold)
        
        # Filter by signal types
        if subscriber.signal_types:
            query &= Q(signal_type__in=subscriber.signal_types)
        
        # Get recent signals (last 24 hours by default)
        since = request.GET.get('since')
        if since:
            try:
                since_date = timezone.datetime.fromisoformat(since.replace('Z', '+00:00'))
                query &= Q(timestamp__gte=since_date)
            except ValueError:
                return JsonResponse({
                    'error': 'Invalid date format',
                    'message': 'Use ISO 8601 format (e.g., 2025-09-01T00:00:00Z)'
                }, status=400)
        else:
            # Default to last 24 hours
            query &= Q(timestamp__gte=timezone.now() - timedelta(hours=24))
        
        # Get signals
        signals = TradingSignal.objects.filter(query).order_by('-timestamp')
        
        # Pagination
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 50)), 100)  # Max 100 per page
        
        paginator = Paginator(signals, per_page)
        page_obj = paginator.get_page(page)
        
        # Format response
        signals_data = []
        for signal in page_obj:
            signal_data = {
                'id': signal.id,
                'ticker': signal.ticker.symbol,
                'signal_type': signal.signal_type,
                'confidence': float(signal.confidence),
                'timestamp': signal.timestamp.isoformat(),
                'source': signal.source,
                'metadata': signal.metadata,
                'related_articles': [
                    {
                        'id': article.id,
                        'title': article.title,
                        'source': article.source,
                        'sentiment': article.gpt_sentiment,
                        'url': article.url
                    }
                    for article in signal.related_articles.all()[:5]  # Limit to 5 articles
                ]
            }
            signals_data.append(signal_data)
        
        return JsonResponse({
            'success': True,
            'data': signals_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginator.count,
                'pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous()
            },
            'subscriber_info': {
                'name': subscriber.name,
                'subscribed_tickers': subscriber.subscribed_tickers,
                'min_confidence_threshold': float(subscriber.min_confidence_threshold),
                'signal_types': subscriber.signal_types
            }
        })
    
    def post(self, request):
        """Generate a new trading signal for a specific ticker"""
        try:
            data = json.loads(request.body)
            ticker = data.get('ticker', '').upper()
            
            if not ticker:
                return JsonResponse({
                    'error': 'Ticker required',
                    'message': 'Please provide a ticker symbol'
                }, status=400)
            
            # Check if subscriber is subscribed to this ticker
            subscriber = request.api_subscriber
            if subscriber.subscribed_tickers and ticker not in subscriber.subscribed_tickers:
                return JsonResponse({
                    'error': 'Ticker not subscribed',
                    'message': f'You are not subscribed to receive signals for {ticker}'
                }, status=403)
            
            # Generate signal
            signal_generator = SignalGenerator()
            signal = signal_generator.generate_signal(ticker, source='api_request')
            
            if signal:
                signal_data = {
                    'id': signal.id,
                    'ticker': signal.ticker.symbol,
                    'signal_type': signal.signal_type,
                    'confidence': float(signal.confidence),
                    'timestamp': signal.timestamp.isoformat(),
                    'source': signal.source,
                    'metadata': signal.metadata
                }
                
                return JsonResponse({
                    'success': True,
                    'message': f'Signal generated for {ticker}',
                    'data': signal_data
                })
            else:
                return JsonResponse({
                    'error': 'Signal generation failed',
                    'message': 'Unable to generate signal for the specified ticker'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'Internal server error',
                'message': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(api_key_required, name='dispatch')
class SignalSubscriptionAPIView(View):
    """
    API endpoint for managing signal subscriptions
    """
    
    def get(self, request):
        """Get current subscription settings"""
        subscriber = request.api_subscriber
        
        return JsonResponse({
            'success': True,
            'data': {
                'name': subscriber.name,
                'status': subscriber.status,
                'subscribed_tickers': subscriber.subscribed_tickers,
                'min_confidence_threshold': float(subscriber.min_confidence_threshold),
                'signal_types': subscriber.signal_types,
                'webhook_url': subscriber.webhook_url,
                'rate_limit_per_hour': subscriber.rate_limit_per_hour,
                'request_count': subscriber.request_count,
                'last_accessed': subscriber.last_accessed.isoformat() if subscriber.last_accessed else None
            }
        })
    
    def post(self, request):
        """Update subscription settings"""
        try:
            data = json.loads(request.body)
            subscriber = request.api_subscriber
            
            # Update allowed fields
            if 'subscribed_tickers' in data:
                subscriber.subscribed_tickers = data['subscribed_tickers']
            
            if 'min_confidence_threshold' in data:
                threshold = float(data['min_confidence_threshold'])
                if 0 <= threshold <= 1:
                    subscriber.min_confidence_threshold = threshold
                else:
                    return JsonResponse({
                        'error': 'Invalid threshold',
                        'message': 'Confidence threshold must be between 0 and 1'
                    }, status=400)
            
            if 'signal_types' in data:
                valid_types = ['buy', 'sell', 'hold']
                signal_types = data['signal_types']
                if all(t in valid_types for t in signal_types):
                    subscriber.signal_types = signal_types
                else:
                    return JsonResponse({
                        'error': 'Invalid signal types',
                        'message': f'Signal types must be one of: {valid_types}'
                    }, status=400)
            
            if 'webhook_url' in data:
                subscriber.webhook_url = data['webhook_url']
            
            subscriber.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Subscription updated successfully',
                'data': {
                    'subscribed_tickers': subscriber.subscribed_tickers,
                    'min_confidence_threshold': float(subscriber.min_confidence_threshold),
                    'signal_types': subscriber.signal_types,
                    'webhook_url': subscriber.webhook_url
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'Internal server error',
                'message': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(webhook_signature_required, name='dispatch')
class WebhookDeliveryStatusView(View):
    """
    API endpoint for webhook delivery status updates
    """
    
    def post(self, request):
        """Update webhook delivery status"""
        try:
            data = json.loads(request.body)
            signal_id = data.get('signal_id')
            status = data.get('status')
            error_message = data.get('error_message', '')
            
            if not signal_id or not status:
                return JsonResponse({
                    'error': 'Missing required fields',
                    'message': 'signal_id and status are required'
                }, status=400)
            
            subscriber = request.api_subscriber
            
            try:
                delivery = SignalDelivery.objects.get(
                    signal_id=signal_id,
                    subscriber=subscriber,
                    delivery_method='webhook'
                )
                
                delivery.status = status
                delivery.delivery_attempts += 1
                delivery.last_attempt = timezone.now()
                
                if status == 'delivered':
                    delivery.delivered_at = timezone.now()
                elif status == 'failed':
                    delivery.error_message = error_message
                
                delivery.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Delivery status updated successfully'
                })
                
            except SignalDelivery.DoesNotExist:
                return JsonResponse({
                    'error': 'Delivery not found',
                    'message': 'No webhook delivery found for the specified signal'
                }, status=404)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON',
                'message': 'Request body must be valid JSON'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'Internal server error',
                'message': str(e)
            }, status=500)


@api_key_required
def api_status(request):
    """Get API status and subscriber information"""
    subscriber = request.api_subscriber
    
    return JsonResponse({
        'success': True,
        'api_version': '1.0',
        'status': 'operational',
        'subscriber': {
            'name': subscriber.name,
            'status': subscriber.status,
            'rate_limit_per_hour': subscriber.rate_limit_per_hour,
            'request_count': subscriber.request_count,
            'last_accessed': subscriber.last_accessed.isoformat() if subscriber.last_accessed else None
        },
        'endpoints': {
            'signals': '/api/v1/signals/',
            'subscription': '/api/v1/subscription/',
            'webhook_status': '/api/v1/webhook/status/',
            'status': '/api/v1/status/'
        }
    })


@api_key_required
def api_documentation(request):
    """Get API documentation"""
    return JsonResponse({
        'success': True,
        'api_version': '1.0',
        'documentation': {
            'authentication': {
                'method': 'API Key',
                'header': 'X-API-Key',
                'description': 'Include your API key in the X-API-Key header'
            },
            'rate_limiting': {
                'limit': '1000 requests per hour (default)',
                'header': 'X-RateLimit-Remaining',
                'description': 'Rate limit information is included in response headers'
            },
            'endpoints': {
                'GET /api/v1/signals/': {
                    'description': 'Retrieve trading signals',
                    'parameters': {
                        'since': 'ISO 8601 timestamp (optional)',
                        'page': 'Page number (default: 1)',
                        'per_page': 'Items per page (max: 100, default: 50)'
                    }
                },
                'POST /api/v1/signals/': {
                    'description': 'Generate a new trading signal',
                    'body': {
                        'ticker': 'Stock ticker symbol (required)'
                    }
                },
                'GET /api/v1/subscription/': {
                    'description': 'Get current subscription settings'
                },
                'POST /api/v1/subscription/': {
                    'description': 'Update subscription settings',
                    'body': {
                        'subscribed_tickers': 'Array of ticker symbols',
                        'min_confidence_threshold': 'Minimum confidence (0-1)',
                        'signal_types': 'Array of signal types (buy, sell, hold)',
                        'webhook_url': 'Webhook URL for real-time delivery'
                    }
                }
            },
            'webhooks': {
                'description': 'Real-time signal delivery via webhooks',
                'authentication': 'X-Webhook-Signature header with HMAC-SHA256',
                'payload': 'JSON with signal data',
                'retry_policy': 'Exponential backoff with max 5 attempts'
            }
        }
    })
