"""
Django management command to create API subscribers
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from main_app.models import APISubscriber


class Command(BaseCommand):
    help = 'Create a new API subscriber for external systems'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Name of the subscriber/company')
        parser.add_argument('email', type=str, help='Contact email address')
        parser.add_argument('--description', type=str, help='Description of the subscriber')
        parser.add_argument('--webhook-url', type=str, help='Webhook URL for real-time delivery')
        parser.add_argument('--tickers', type=str, nargs='+', help='List of ticker symbols to subscribe to')
        parser.add_argument('--signal-types', type=str, nargs='+', choices=['buy', 'sell', 'hold'], 
                          help='Types of signals to receive')
        parser.add_argument('--confidence-threshold', type=float, default=0.50,
                          help='Minimum confidence threshold (0-1)')
        parser.add_argument('--rate-limit', type=int, default=1000,
                          help='Rate limit per hour')
        parser.add_argument('--status', type=str, choices=['active', 'inactive', 'pending'], 
                          default='active', help='Initial status')

    def handle(self, *args, **options):
        name = options['name']
        email = options['email']
        
        # Validate email
        try:
            validate_email(email)
        except:
            raise CommandError(f'Invalid email address: {email}')
        
        # Check if subscriber already exists
        if APISubscriber.objects.filter(name=name).exists():
            raise CommandError(f'Subscriber with name "{name}" already exists')
        
        if APISubscriber.objects.filter(contact_email=email).exists():
            raise CommandError(f'Subscriber with email "{email}" already exists')
        
        # Create subscriber
        subscriber = APISubscriber(
            name=name,
            contact_email=email,
            description=options.get('description', ''),
            webhook_url=options.get('webhook_url', ''),
            subscribed_tickers=options.get('tickers', []),
            signal_types=options.get('signal_types', ['buy', 'sell', 'hold']),
            min_confidence_threshold=options['confidence_threshold'],
            rate_limit_per_hour=options['rate_limit'],
            status=options['status']
        )
        
        subscriber.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created API subscriber: {name}')
        )
        self.stdout.write(f'API Key: {subscriber.api_key}')
        self.stdout.write(f'Secret Key: {subscriber.secret_key}')
        self.stdout.write(f'Status: {subscriber.status}')
        self.stdout.write(f'Rate Limit: {subscriber.rate_limit_per_hour} requests/hour')
        
        if subscriber.webhook_url:
            self.stdout.write(f'Webhook URL: {subscriber.webhook_url}')
        
        if subscriber.subscribed_tickers:
            self.stdout.write(f'Subscribed Tickers: {", ".join(subscriber.subscribed_tickers)}')
        
        self.stdout.write(f'Signal Types: {", ".join(subscriber.signal_types)}')
        self.stdout.write(f'Confidence Threshold: {subscriber.min_confidence_threshold}')


