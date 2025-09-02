from django.core.management.base import BaseCommand
from django.db.models import Q
from main_app.models import NewsArticle
from main_app.gpt_service import GPTNewsAnalyzer
import time
from django.db.models import Count
from django.utils import timezone

class Command(BaseCommand):
    help = 'Analyze news articles using GPT for sentiment and impact classification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Number of articles to analyze (default: 10)'
        )
        parser.add_argument(
            '--source',
            type=str,
            help='Filter articles by source (e.g., reuters, bloomberg)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-analysis of already analyzed articles'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be analyzed without actually doing it'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        source_filter = options['source']
        force = options['force']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS(f'🚀 Starting news analysis...'))
        
        # Build query
        if force:
            # Include all articles
            articles_query = NewsArticle.objects.all()
            self.stdout.write('⚠️ Force mode: Will re-analyze all articles')
        else:
            # Only unanalyzed articles
            articles_query = NewsArticle.objects.filter(
                Q(gpt_sentiment__isnull=True) | Q(gpt_impact__isnull=True)
            )
            self.stdout.write('📝 Mode: Will analyze only unanalyzed articles')
        
        # Apply source filter if specified
        if source_filter:
            articles_query = articles_query.filter(source=source_filter)
            self.stdout.write(f'🎯 Source filter: {source_filter}')
        
        # Get articles
        articles = list(articles_query[:limit])
        
        if not articles:
            self.stdout.write(self.style.WARNING('❌ No articles found to analyze'))
            return
        
        self.stdout.write(f'📊 Found {len(articles)} articles to analyze')
        
        if dry_run:
            self.stdout.write('🔍 DRY RUN - Would analyze the following articles:')
            for i, article in enumerate(articles, 1):
                self.stdout.write(f'  {i}. {article.title[:60]}... ({article.source})')
            return
        
        # Initialize GPT analyzer
        gpt_analyzer = GPTNewsAnalyzer()
        
        # Check if GPT is available
        if not gpt_analyzer.api_key:
            self.stdout.write(self.style.ERROR('❌ OpenAI API key not configured'))
            self.stdout.write('Please set OPENAI_API_KEY in your environment or Django settings')
            return
        
        # Analyze articles
        success_count = 0
        error_count = 0
        
        for i, article in enumerate(articles, 1):
            try:
                self.stdout.write(f'🔍 Analyzing article {i}/{len(articles)}: {article.title[:60]}...')
                
                # Analyze sentiment
                sentiment_result = gpt_analyzer.analyze_article_sentiment(article)
                
                # Analyze impact
                impact_result = gpt_analyzer.classify_news_impact(article)
                
                # Update article
                article.gpt_sentiment = sentiment_result.get('sentiment')
                article.gpt_sentiment_confidence = sentiment_result.get('confidence')
                article.gpt_sentiment_reason = sentiment_result.get('reason', '')
                article.gpt_impact = impact_result.get('impact')
                article.gpt_impact_confidence = impact_result.get('confidence')
                article.gpt_sectors = impact_result.get('sectors', [])
                article.gpt_analysis_date = timezone.now()
                article.gpt_model_used = sentiment_result.get('model', 'gpt-3.5-turbo')
                article.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Article {i} analyzed: '
                        f'Sentiment={sentiment_result.get("sentiment", "N/A")} '
                        f'({sentiment_result.get("confidence", 0):.2f}), '
                        f'Impact={impact_result.get("impact", "N/A")} '
                        f'({impact_result.get("confidence", 0):.2f})'
                    )
                )
                
                success_count += 1
                
                # Small delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error analyzing article {i}: {e}')
                )
                error_count += 1
                continue
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'🎉 Analysis completed!'))
        self.stdout.write(f'📊 Total articles: {len(articles)}')
        self.stdout.write(f'✅ Successfully analyzed: {success_count}')
        self.stdout.write(f'❌ Errors: {error_count}')
        
        if success_count > 0:
            # Show some statistics
            total_articles = NewsArticle.objects.count()
            analyzed_articles = NewsArticle.objects.exclude(
                Q(gpt_sentiment__isnull=True) & Q(gpt_impact__isnull=True)
            ).count()
            
            self.stdout.write(f'📈 Overall progress: {analyzed_articles}/{total_articles} articles analyzed')
            self.stdout.write(f'📊 Analysis percentage: {(analyzed_articles/total_articles*100):.1f}%')
            
            # Show sentiment distribution
            sentiment_stats = NewsArticle.objects.exclude(
                gpt_sentiment__isnull=True
            ).values('gpt_sentiment').annotate(count=Count('id'))
            
            if sentiment_stats:
                self.stdout.write('\n📊 Sentiment Distribution:')
                for stat in sentiment_stats:
                    self.stdout.write(f'  {stat["gpt_sentiment"]}: {stat["count"]}')
            
            # Show impact distribution
            impact_stats = NewsArticle.objects.exclude(
                gpt_impact__isnull=True
            ).values('gpt_impact').annotate(count=Count('id'))
            
            if impact_stats:
                self.stdout.write('\n🎯 Impact Distribution:')
                for stat in impact_stats:
                    self.stdout.write(f'  {stat["gpt_impact"]}: {stat["count"]}')
        
        self.stdout.write('='*50)



