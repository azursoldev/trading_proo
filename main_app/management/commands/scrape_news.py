from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from main_app.scrapers import ScrapingManager
from main_app.models import APIConfig


class Command(BaseCommand):
    help = 'Scrape financial news from various sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['reuters', 'bloomberg', 'yahoo_finance', 'marketwatch', 'cnbc', 'finnhub', 'all'],
            default='reuters',
            help='Source to scrape from (default: reuters)'
        )
        parser.add_argument(
            '--max-articles',
            type=int,
            default=20,
            help='Maximum number of articles to scrape (default: 20)'
        )
        parser.add_argument(
            '--symbol',
            type=str,
            help='Company symbol for FinnHub scraping (e.g., AAPL)'
        )
        parser.add_argument(
            '--save-db',
            action='store_true',
            default=True,
            help='Save scraped articles to database (default: True)'
        )

    def handle(self, *args, **options):
        source = options['source']
        max_articles = options['max_articles']
        symbol = options['symbol']
        save_db = options['save_db']

        self.stdout.write(
            self.style.SUCCESS(f'🚀 Starting news scraping from {source}')
        )

        manager = ScrapingManager()

        try:
            if source == 'reuters' or source == 'all':
                self.stdout.write('📰 Scraping Reuters...')
                articles = manager.scrape_reuters(
                    max_articles=max_articles, 
                    save_to_db=save_db
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Scraped {len(articles)} articles from Reuters')
                )

            if source == 'bloomberg' or source == 'all':
                self.stdout.write('📰 Scraping Bloomberg...')
                articles = manager.scrape_bloomberg(
                    max_articles=max_articles, 
                    save_to_db=save_db
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Scraped {len(articles)} articles from Bloomberg')
                )

            if source == 'yahoo_finance' or source == 'all':
                self.stdout.write('📰 Scraping Yahoo Finance...')
                articles = manager.scrape_yahoo_finance(
                    max_articles=max_articles, 
                    save_to_db=save_db
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Scraped {len(articles)} articles from Yahoo Finance')
                )

            if source == 'marketwatch' or source == 'all':
                self.stdout.write('📰 Scraping MarketWatch...')
                articles = manager.scrape_marketwatch(
                    max_articles=max_articles, 
                    save_to_db=save_db
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Scraped {len(articles)} articles from MarketWatch')
                )

            if source == 'cnbc' or source == 'all':
                self.stdout.write('📰 Scraping CNBC...')
                articles = manager.scrape_cnbc(
                    max_articles=max_articles, 
                    save_to_db=save_db
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Scraped {len(articles)} articles from CNBC')
                )

            if source == 'finnhub' or source == 'all':
                # Check if FinnHub API key is configured
                try:
                    api_config = APIConfig.objects.get(name='finnhub', is_active=True)
                    manager.setup_finnhub(api_config.api_key)
                    
                    if symbol:
                        self.stdout.write(f'📰 Scraping FinnHub for {symbol}...')
                        articles = manager.scrape_finnhub(
                            symbol=symbol, 
                            save_to_db=save_db
                        )
                    else:
                        self.stdout.write('📰 Scraping FinnHub market news...')
                        articles = manager.scrape_finnhub(save_to_db=save_db)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Scraped {len(articles)} articles from FinnHub')
                    )
                    
                except APIConfig.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            '⚠️ FinnHub API key not configured. '
                            'Use /api-config/ to add your API key.'
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS('🎉 News scraping completed successfully!')
            )

        except Exception as e:
            raise CommandError(f'Error during scraping: {str(e)}')
