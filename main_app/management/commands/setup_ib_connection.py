from django.core.management.base import BaseCommand, CommandError
from main_app.models import IBConnection, MarketTicker
from main_app.ib_service import MarketDataManager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Setup Interactive Brokers connection and test connectivity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='default',
            help='Connection name (default: default)'
        )
        parser.add_argument(
            '--host',
            type=str,
            default='127.0.0.1',
            help='IB host (default: 127.0.0.1)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=7497,
            help='IB port - TWS: 7497, IB Gateway: 4001 (default: 7497)'
        )
        parser.add_argument(
            '--client-id',
            type=int,
            default=1,
            help='Client ID (default: 1)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test the connection after setup'
        )
        parser.add_argument(
            '--add-popular-tickers',
            action='store_true',
            help='Add popular tickers to database'
        )

    def handle(self, *args, **options):
        name = options['name']
        host = options['host']
        port = options['port']
        client_id = options['client_id']
        test_connection = options['test']
        add_tickers = options['add_popular_tickers']

        self.stdout.write(self.style.SUCCESS('🔧 Setting up IB connection...'))

        try:
            # Create or update connection
            connection, created = IBConnection.objects.get_or_create(
                name=name,
                defaults={
                    'host': host,
                    'port': port,
                    'client_id': client_id,
                    'status': 'disconnected'
                }
            )

            if not created:
                # Update existing connection
                connection.host = host
                connection.port = port
                connection.client_id = client_id
                connection.save()

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f'✅ {action} IB connection: {name} ({host}:{port})')
            )

            # Add popular tickers if requested
            if add_tickers:
                self.stdout.write('📊 Adding popular tickers...')
                self._add_popular_tickers()
                self.stdout.write(self.style.SUCCESS('✅ Popular tickers added'))

            # Test connection if requested
            if test_connection:
                self.stdout.write('🧪 Testing connection...')
                if self._test_connection(connection):
                    self.stdout.write(self.style.SUCCESS('✅ Connection test successful'))
                else:
                    self.stdout.write(self.style.ERROR('❌ Connection test failed'))

        except Exception as e:
            logger.error(f"Error setting up IB connection: {e}")
            raise CommandError(f'Failed to setup IB connection: {str(e)}')

    def _add_popular_tickers(self):
        """Add popular ticker symbols to database"""
        popular_tickers = [
            # Tech Giants
            {'symbol': 'AAPL', 'company_name': 'Apple Inc.', 'sector': 'Technology'},
            {'symbol': 'MSFT', 'company_name': 'Microsoft Corporation', 'sector': 'Technology'},
            {'symbol': 'GOOGL', 'company_name': 'Alphabet Inc.', 'sector': 'Technology'},
            {'symbol': 'AMZN', 'company_name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'TSLA', 'company_name': 'Tesla Inc.', 'sector': 'Consumer Discretionary'},
            {'symbol': 'META', 'company_name': 'Meta Platforms Inc.', 'sector': 'Technology'},
            {'symbol': 'NVDA', 'company_name': 'NVIDIA Corporation', 'sector': 'Technology'},
            {'symbol': 'NFLX', 'company_name': 'Netflix Inc.', 'sector': 'Communication Services'},
            
            # Semiconductor
            {'symbol': 'AMD', 'company_name': 'Advanced Micro Devices Inc.', 'sector': 'Technology'},
            {'symbol': 'INTC', 'company_name': 'Intel Corporation', 'sector': 'Technology'},
            
            # Software
            {'symbol': 'CRM', 'company_name': 'Salesforce Inc.', 'sector': 'Technology'},
            {'symbol': 'ADBE', 'company_name': 'Adobe Inc.', 'sector': 'Technology'},
            {'symbol': 'ORCL', 'company_name': 'Oracle Corporation', 'sector': 'Technology'},
            
            # Financial
            {'symbol': 'JPM', 'company_name': 'JPMorgan Chase & Co.', 'sector': 'Financials'},
            {'symbol': 'BAC', 'company_name': 'Bank of America Corporation', 'sector': 'Financials'},
            {'symbol': 'WFC', 'company_name': 'Wells Fargo & Company', 'sector': 'Financials'},
            {'symbol': 'GS', 'company_name': 'Goldman Sachs Group Inc.', 'sector': 'Financials'},
            
            # Healthcare
            {'symbol': 'JNJ', 'company_name': 'Johnson & Johnson', 'sector': 'Healthcare'},
            {'symbol': 'PFE', 'company_name': 'Pfizer Inc.', 'sector': 'Healthcare'},
            {'symbol': 'UNH', 'company_name': 'UnitedHealth Group Inc.', 'sector': 'Healthcare'},
            
            # Consumer
            {'symbol': 'KO', 'company_name': 'The Coca-Cola Company', 'sector': 'Consumer Staples'},
            {'symbol': 'PEP', 'company_name': 'PepsiCo Inc.', 'sector': 'Consumer Staples'},
            {'symbol': 'WMT', 'company_name': 'Walmart Inc.', 'sector': 'Consumer Staples'},
            {'symbol': 'PG', 'company_name': 'Procter & Gamble Co.', 'sector': 'Consumer Staples'},
            
            # Energy
            {'symbol': 'XOM', 'company_name': 'Exxon Mobil Corporation', 'sector': 'Energy'},
            {'symbol': 'CVX', 'company_name': 'Chevron Corporation', 'sector': 'Energy'},
            
            # Industrial
            {'symbol': 'BA', 'company_name': 'The Boeing Company', 'sector': 'Industrials'},
            {'symbol': 'CAT', 'company_name': 'Caterpillar Inc.', 'sector': 'Industrials'},
            {'symbol': 'GE', 'company_name': 'General Electric Company', 'sector': 'Industrials'},
            
            # Communication
            {'symbol': 'VZ', 'company_name': 'Verizon Communications Inc.', 'sector': 'Communication Services'},
            {'symbol': 'T', 'company_name': 'AT&T Inc.', 'sector': 'Communication Services'},
            
            # ETFs
            {'symbol': 'SPY', 'company_name': 'SPDR S&P 500 ETF Trust', 'sector': 'ETF'},
            {'symbol': 'QQQ', 'company_name': 'Invesco QQQ Trust', 'sector': 'ETF'},
            {'symbol': 'IWM', 'company_name': 'iShares Russell 2000 ETF', 'sector': 'ETF'},
            {'symbol': 'VTI', 'company_name': 'Vanguard Total Stock Market ETF', 'sector': 'ETF'},
        ]

        added_count = 0
        for ticker_data in popular_tickers:
            ticker, created = MarketTicker.objects.get_or_create(
                symbol=ticker_data['symbol'],
                defaults={
                    'company_name': ticker_data['company_name'],
                    'sector': ticker_data['sector'],
                    'exchange': 'SMART',
                    'security_type': 'STK',
                    'currency': 'USD',
                    'is_active': True,
                    'is_tradable': True
                }
            )
            if created:
                added_count += 1

        self.stdout.write(f'📊 Added {added_count} new tickers to database')

    def _test_connection(self, connection):
        """Test IB connection"""
        try:
            manager = MarketDataManager()
            manager.set_connection(connection)
            
            if manager.connect():
                # Test with a simple request
                test_ticker = MarketTicker.objects.filter(symbol='AAPL').first()
                if test_ticker:
                    success = manager.start_real_time_data(['AAPL'])
                    if success:
                        manager.disconnect()
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
