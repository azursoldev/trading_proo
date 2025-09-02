"""
Webhook Delivery Service for Trading Pro
Handles real-time delivery of trading signals to external subscribers
"""

import json
import requests
import time
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .models import APISubscriber, SignalDelivery, TradingSignal
from .api_auth import generate_webhook_signature
import logging

logger = logging.getLogger(__name__)


class WebhookDeliveryService:
    """
    Service for delivering trading signals to external subscribers via webhooks
    """
    
    def __init__(self):
        self.max_retry_attempts = 5
        self.retry_delays = [1, 5, 15, 60, 300]  # seconds
    
    def deliver_signal_to_subscriber(self, signal, subscriber):
        """
        Deliver a trading signal to a specific subscriber
        """
        if not subscriber.webhook_url:
            logger.warning(f"No webhook URL configured for subscriber {subscriber.name}")
            return False
        
        # Create delivery record
        delivery, created = SignalDelivery.objects.get_or_create(
            signal=signal,
            subscriber=subscriber,
            defaults={
                'delivery_method': 'webhook',
                'status': 'pending'
            }
        )
        
        if not created and delivery.status == 'delivered':
            logger.info(f"Signal {signal.id} already delivered to {subscriber.name}")
            return True
        
        # Prepare payload
        payload = self._prepare_signal_payload(signal)
        
        # Deliver via webhook
        success = self._deliver_webhook(subscriber, payload, delivery)
        
        return success
    
    def _prepare_signal_payload(self, signal):
        """
        Prepare the signal payload for webhook delivery
        """
        payload = {
            'event_type': 'trading_signal',
            'signal_id': signal.id,
            'ticker': signal.ticker,
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
                for article in signal.related_articles.all()[:5]
            ]
        }
        
        return payload
    
    def _deliver_webhook(self, subscriber, payload, delivery):
        """
        Deliver webhook to subscriber with retry logic
        """
        payload_json = json.dumps(payload)
        signature = generate_webhook_signature(subscriber.secret_key, payload_json.encode('utf-8'))
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': subscriber.api_key,
            'X-Webhook-Signature': signature,
            'X-Webhook-Event': 'trading_signal',
            'User-Agent': 'TradingPro-Webhook/1.0'
        }
        
        for attempt in range(self.max_retry_attempts):
            try:
                delivery.delivery_attempts += 1
                delivery.last_attempt = timezone.now()
                delivery.status = 'retrying' if attempt > 0 else 'pending'
                delivery.save()
                
                response = requests.post(
                    subscriber.webhook_url,
                    data=payload_json,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    delivery.status = 'delivered'
                    delivery.delivered_at = timezone.now()
                    delivery.error_message = ''
                    delivery.save()
                    
                    logger.info(f"Successfully delivered signal {delivery.signal.id} to {subscriber.name}")
                    return True
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    delivery.error_message = error_msg
                    delivery.save()
                    
                    logger.warning(f"Webhook delivery failed for {subscriber.name}: {error_msg}")
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Request error: {str(e)}"
                delivery.error_message = error_msg
                delivery.save()
                
                logger.error(f"Webhook delivery error for {subscriber.name}: {error_msg}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retry_attempts - 1:
                delay = self.retry_delays[attempt]
                delivery.next_retry = timezone.now() + timedelta(seconds=delay)
                delivery.save()
                time.sleep(delay)
        
        # All attempts failed
        delivery.status = 'failed'
        delivery.save()
        
        logger.error(f"Failed to deliver signal {delivery.signal.id} to {subscriber.name} after {self.max_retry_attempts} attempts")
        return False
    
    def deliver_signal_to_all_subscribers(self, signal):
        """
        Deliver a trading signal to all active subscribers
        """
        # Get active subscribers who are subscribed to this ticker
        subscribers = APISubscriber.objects.filter(
            status='active',
            webhook_url__isnull=False
        ).exclude(webhook_url='')
        
        # Filter by ticker subscription if specified
        if signal.ticker:
            subscribers = subscribers.filter(
                Q(subscribed_tickers__contains=[signal.ticker]) | 
                Q(subscribed_tickers__isnull=True) |
                Q(subscribed_tickers=[])
            )
        
        # Filter by confidence threshold
        subscribers = subscribers.filter(
            min_confidence_threshold__lte=signal.confidence
        )
        
        # Filter by signal type
        if signal.signal_type:
            subscribers = subscribers.filter(
                Q(signal_types__contains=[signal.signal_type]) |
                Q(signal_types__isnull=True) |
                Q(signal_types=[])
            )
        
        delivery_results = []
        for subscriber in subscribers:
            success = self.deliver_signal_to_subscriber(signal, subscriber)
            delivery_results.append({
                'subscriber': subscriber.name,
                'success': success
            })
        
        logger.info(f"Delivered signal {signal.id} to {len(subscribers)} subscribers")
        return delivery_results
    
    def retry_failed_deliveries(self):
        """
        Retry failed webhook deliveries
        """
        # Get deliveries that should be retried
        now = timezone.now()
        failed_deliveries = SignalDelivery.objects.filter(
            status='failed',
            next_retry__lte=now,
            delivery_attempts__lt=self.max_retry_attempts
        )
        
        retry_count = 0
        for delivery in failed_deliveries:
            payload = self._prepare_signal_payload(delivery.signal)
            success = self._deliver_webhook(delivery.subscriber, payload, delivery)
            
            if success:
                retry_count += 1
        
        logger.info(f"Retried {retry_count} failed deliveries")
        return retry_count
    
    def get_delivery_stats(self, subscriber=None):
        """
        Get delivery statistics for a subscriber or all subscribers
        """
        if subscriber:
            deliveries = SignalDelivery.objects.filter(subscriber=subscriber)
        else:
            deliveries = SignalDelivery.objects.all()
        
        stats = {
            'total_deliveries': deliveries.count(),
            'delivered': deliveries.filter(status='delivered').count(),
            'failed': deliveries.filter(status='failed').count(),
            'pending': deliveries.filter(status='pending').count(),
            'retrying': deliveries.filter(status='retrying').count(),
            'success_rate': 0
        }
        
        if stats['total_deliveries'] > 0:
            stats['success_rate'] = (stats['delivered'] / stats['total_deliveries']) * 100
        
        return stats


# Global webhook service instance
webhook_service = WebhookDeliveryService()


def deliver_signal_webhook(signal_id):
    """
    Celery task to deliver signal via webhook
    """
    try:
        signal = TradingSignal.objects.get(id=signal_id)
        return webhook_service.deliver_signal_to_all_subscribers(signal)
    except TradingSignal.DoesNotExist:
        logger.error(f"Signal {signal_id} not found for webhook delivery")
        return False


