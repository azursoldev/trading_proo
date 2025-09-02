"""
Django management command to generate trading signals
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from main_app.models import MarketTicker, TradingSignal
from main_app.signal_service import SignalGenerator, SignalManager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate trading signals for tickers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tickers',
            type=str,
            help='Comma-separated list of ticker symbols to generate signals for',
        )
        parser.add_argument(
            '--source',
            type=str,
            choices=['gpt_analysis', 'market_data', 'combined'],
            default='combined',
            help='Signal generation source (default: combined)',
        )
        parser.add_argument(
            '--all-active',
            action='store_true',
            help='Generate signals for all active tickers',
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.0,
            help='Minimum confidence threshold for generated signals (default: 0.0)',
        )
        parser.add_argument(
            '--expire-old',
            action='store_true',
            help='Expire old signals before generating new ones',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting signal generation...')
        )

        # Expire old signals if requested
        if options['expire_old']:
            expired_count = SignalManager.expire_old_signals()
            self.stdout.write(
                self.style.WARNING(f'Expired {expired_count} old signals')
            )

        # Determine tickers to process
        tickers_to_process = []
        
        if options['tickers']:
            ticker_symbols = [t.strip().upper() for t in options['tickers'].split(',')]
            for symbol in ticker_symbols:
                ticker = MarketTicker.objects.filter(symbol=symbol).first()
                if ticker:
                    tickers_to_process.append(ticker)
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Ticker {symbol} not found in database')
                    )
        
        elif options['all_active']:
            tickers_to_process = list(MarketTicker.objects.filter(is_active=True))
        
        else:
            # Default: process popular tickers
            popular_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX']
            for symbol in popular_tickers:
                ticker = MarketTicker.objects.filter(symbol=symbol).first()
                if ticker:
                    tickers_to_process.append(ticker)
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Ticker {symbol} not found, skipping...')
                    )

        if not tickers_to_process:
            raise CommandError('No tickers to process')

        # Generate signals
        signal_generator = SignalGenerator()
        generated_count = 0
        skipped_count = 0

        for ticker in tickers_to_process:
            try:
                self.stdout.write(f'Generating signal for {ticker.symbol}...')
                
                signal = signal_generator.generate_signal(
                    ticker.symbol, 
                    source=options['source']
                )
                
                if signal:
                    if signal.confidence >= options['min_confidence']:
                        generated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Generated {signal.signal_type} signal for {ticker.symbol} '
                                f'(confidence: {signal.confidence:.2f})'
                            )
                        )
                    else:
                        signal.delete()  # Remove low confidence signals
                        skipped_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠ Skipped {ticker.symbol} - confidence too low '
                                f'({signal.confidence:.2f} < {options["min_confidence"]})'
                            )
                        )
                else:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⚠ No signal generated for {ticker.symbol}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error generating signal for {ticker.symbol}: {str(e)}')
                )
                logger.error(f'Error generating signal for {ticker.symbol}: {str(e)}')

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'Signal generation completed!')
        )
        self.stdout.write(f'Generated: {generated_count} signals')
        self.stdout.write(f'Skipped: {skipped_count} tickers')
        self.stdout.write(f'Source: {options["source"]}')
        self.stdout.write(f'Min confidence: {options["min_confidence"]}')

        # Show recent signals
        recent_signals = TradingSignal.objects.filter(
            timestamp__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).order_by('-timestamp')[:5]

        if recent_signals:
            self.stdout.write('\nRecent signals:')
            for signal in recent_signals:
                self.stdout.write(
                    f'  {signal.ticker.symbol}: {signal.signal_type} '
                    f'({signal.confidence:.2f}) - {signal.timestamp.strftime("%H:%M")}'
                )
