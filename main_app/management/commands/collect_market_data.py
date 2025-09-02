from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from main_app.models import MarketTicker, IBConnection, DataCollectionJob
from main_app.ib_service import MarketDataManager
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Collect market data from Interactive Brokers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--connection',
            type=str,
            help='IB connection name to use'
        )
        parser.add_argument(
            '--tickers',
            nargs='+',
            help='List of ticker symbols to collect data for'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['realtime', 'historical', 'both'],
            default='both',
            help='Type of data to collect (default: both)'
        )
        parser.add_argument(
            '--timeframe',
            type=str,
            default='1 D',
            help='Timeframe for historical data (default: 1 D)'
        )
        parser.add_argument(
            '--duration',
            type=str,
            default='1 Y',
            help='Duration for historical data (default: 1 Y)'
        )
        parser.add_argument(
            '--bar-size',
            type=str,
            default='1 day',
            help='Bar size for historical data (default: 1 day)'
        )
        parser.add_argument(
            '--popular',
            action='store_true',
            help='Use popular tickers list'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=300,
            help='Timeout in seconds for data collection (default: 300)'
        )

    def handle(self, *args, **options):
        connection_name = options['connection']
        tickers = options['tickers']
        data_type = options['type']
        timeframe = options['timeframe']
        duration = options['duration']
        bar_size = options['bar_size']
        use_popular = options['popular']
        timeout = options['timeout']

        self.stdout.write(self.style.SUCCESS('🚀 Starting market data collection...'))

        # Initialize market data manager
        manager = MarketDataManager()
        
        # Setup connection
        if not manager.setup_connection(connection_name):
            raise CommandError('Failed to setup IB connection')

        # Get tickers to process
        if use_popular:
            tickers = manager.get_popular_tickers()
            self.stdout.write(f'📊 Using popular tickers: {", ".join(tickers[:10])}...')
        elif not tickers:
            # Get all active tickers from database
            tickers = list(MarketTicker.objects.filter(is_active=True).values_list('symbol', flat=True))
            if not tickers:
                self.stdout.write(self.style.WARNING('⚠️ No tickers found in database'))
                return
            self.stdout.write(f'📊 Using all active tickers: {len(tickers)} tickers')

        # Create data collection job
        job = DataCollectionJob.objects.create(
            job_type='realtime' if data_type == 'realtime' else 'historical',
            tickers=tickers,
            timeframe=timeframe,
            start_date=timezone.now(),
            total_items=len(tickers)
        )

        try:
            # Connect to IB
            self.stdout.write('🔌 Connecting to Interactive Brokers...')
            if not manager.connect():
                raise CommandError('Failed to connect to IB')

            self.stdout.write(self.style.SUCCESS('✅ Connected to IB successfully'))

            # Start data collection
            if data_type in ['realtime', 'both']:
                self.stdout.write('📈 Starting real-time data collection...')
                if manager.start_real_time_data(tickers):
                    self.stdout.write(self.style.SUCCESS('✅ Real-time data collection started'))
                    job.successful_items += len(tickers)
                else:
                    self.stdout.write(self.style.ERROR('❌ Failed to start real-time data collection'))

            if data_type in ['historical', 'both']:
                self.stdout.write('📊 Starting historical data collection...')
                if manager.collect_historical_data(tickers, timeframe, duration, bar_size):
                    self.stdout.write(self.style.SUCCESS('✅ Historical data collection started'))
                    job.successful_items += len(tickers)
                else:
                    self.stdout.write(self.style.ERROR('❌ Failed to start historical data collection'))

            # Wait for data collection
            self.stdout.write(f'⏳ Waiting for data collection (timeout: {timeout}s)...')
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                time.sleep(5)
                
                # Check if we have enough data
                if self._check_data_collection_progress(tickers):
                    self.stdout.write(self.style.SUCCESS('✅ Data collection completed'))
                    break
                
                # Show progress
                elapsed = int(time.time() - start_time)
                self.stdout.write(f'⏳ Still collecting data... ({elapsed}s elapsed)')

            # Update job status
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save()

            self.stdout.write(self.style.SUCCESS('🎉 Market data collection completed!'))

        except Exception as e:
            logger.error(f"Error in market data collection: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            raise CommandError(f'Market data collection failed: {str(e)}')

        finally:
            # Disconnect from IB
            manager.disconnect()
            self.stdout.write('🔌 Disconnected from IB')

    def _check_data_collection_progress(self, tickers):
        """Check if data collection has made sufficient progress"""
        from main_app.models import MarketData, HistoricalData
        
        # Check real-time data
        realtime_count = MarketData.objects.filter(
            ticker__symbol__in=tickers,
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        
        # Check historical data
        historical_count = HistoricalData.objects.filter(
            ticker__symbol__in=tickers
        ).count()
        
        # Consider collection complete if we have data for at least 50% of tickers
        min_expected = len(tickers) * 0.5
        
        return realtime_count >= min_expected or historical_count >= min_expected
