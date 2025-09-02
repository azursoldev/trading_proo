from django.core.management.base import BaseCommand
from django.utils import timezone
from main_app.models import NewsArticle
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Create test articles for testing the news system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test articles to create (default: 5)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(
            self.style.SUCCESS(f'🚀 Creating {count} test articles...')
        )

        # Sample article data
        sample_articles = [
            {
                'title': 'Breaking: Major Market Rally Continues as Tech Stocks Soar',
                'content': 'Technology stocks led a broad market rally today, with the NASDAQ reaching new record highs. Analysts attribute the surge to strong earnings reports and positive economic data. The rally was led by major tech companies including Apple, Microsoft, and Google parent Alphabet.',
                'summary': 'Technology stocks led a broad market rally today, with the NASDAQ reaching new record highs.',
                'url': 'https://example.com/article1',
                'source': 'reuters',
                'author': 'Financial Reporter',
                'category': 'Markets',
                'tags': ['markets', 'technology', 'rally'],
                'published_date': timezone.now() - timedelta(hours=2)
            },
            {
                'title': 'Federal Reserve Signals Potential Rate Cut in Next Meeting',
                'content': 'Federal Reserve officials have indicated they may consider cutting interest rates at their next policy meeting. This comes amid concerns about economic growth and inflation levels. The potential rate cut could provide stimulus to the economy and boost market sentiment.',
                'summary': 'Federal Reserve officials have indicated they may consider cutting interest rates at their next policy meeting.',
                'url': 'https://example.com/article2',
                'source': 'bloomberg',
                'author': 'Central Bank Analyst',
                'category': 'Monetary Policy',
                'tags': ['federal reserve', 'interest rates', 'monetary policy'],
                'published_date': timezone.now() - timedelta(hours=4)
            },
            {
                'title': 'Oil Prices Surge on Middle East Supply Concerns',
                'content': 'Oil prices jumped sharply today as tensions in the Middle East raised concerns about potential supply disruptions. Brent crude futures rose by over 3% while West Texas Intermediate also saw significant gains. Energy analysts warn that further geopolitical tensions could push prices even higher.',
                'summary': 'Oil prices jumped sharply today as tensions in the Middle East raised concerns about potential supply disruptions.',
                'url': 'https://example.com/article3',
                'source': 'yahoo_finance',
                'author': 'Energy Correspondent',
                'category': 'Commodities',
                'tags': ['oil', 'energy', 'geopolitics', 'commodities'],
                'published_date': timezone.now() - timedelta(hours=6)
            },
            {
                'title': 'European Markets Open Higher on Strong Corporate Earnings',
                'content': 'European stock markets opened higher this morning, buoyed by strong corporate earnings reports from major companies. The FTSE 100, DAX, and CAC 40 all showed positive momentum in early trading. Banking and automotive sectors were among the top performers.',
                'summary': 'European stock markets opened higher this morning, buoyed by strong corporate earnings reports from major companies.',
                'url': 'https://example.com/article4',
                'source': 'marketwatch',
                'author': 'European Markets Reporter',
                'category': 'International Markets',
                'tags': ['europe', 'markets', 'earnings', 'stocks'],
                'published_date': timezone.now() - timedelta(hours=8)
            },
            {
                'title': 'Cryptocurrency Market Shows Signs of Recovery',
                'content': 'The cryptocurrency market is showing signs of recovery after recent volatility. Bitcoin has regained the $50,000 level while Ethereum and other major altcoins also posted gains. Analysts suggest that institutional adoption and regulatory clarity are driving the positive momentum.',
                'summary': 'The cryptocurrency market is showing signs of recovery after recent volatility.',
                'url': 'https://example.com/article5',
                'source': 'cnbc',
                'author': 'Crypto Analyst',
                'category': 'Cryptocurrency',
                'tags': ['cryptocurrency', 'bitcoin', 'ethereum', 'digital assets'],
                'published_date': timezone.now() - timedelta(hours=10)
            }
        ]

        created_count = 0
        for i, article_data in enumerate(sample_articles[:count]):
            try:
                # Check if article already exists
                if NewsArticle.objects.filter(title=article_data['title']).exists():
                    self.stdout.write(f'⚠️ Article {i+1} already exists, skipping...')
                    continue
                
                # Create new article
                article = NewsArticle(
                    title=article_data['title'],
                    content=article_data['content'],
                    summary=article_data['summary'],
                    url=article_data['url'],
                    source=article_data['source'],
                    published_date=article_data['published_date'],
                    author=article_data['author'],
                    category=article_data['category'],
                    tags=article_data['tags']
                )
                article.save()
                created_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created article {i+1}: {article.title[:50]}...')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error creating article {i+1}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'🎉 Successfully created {created_count} test articles!')
        )
        
        # Show summary
        total_articles = NewsArticle.objects.count()
        self.stdout.write(f'📊 Total articles in database: {total_articles}')
        
        # Show articles by source
        from django.db.models import Count
        source_counts = NewsArticle.objects.values('source').annotate(count=Count('id'))
        self.stdout.write('📈 Articles by source:')
        for source_count in source_counts:
            self.stdout.write(f'  - {source_count["source"]}: {source_count["count"]}')



