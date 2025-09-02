from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging

from .models import (
    NewsArticle, ScrapingSession, APIConfig, TradingRecommendation, NewsAnalysis,
    MarketTicker, MarketData, HistoricalData, IBConnection, DataCollectionJob,
    TradingSignal, SignalMetadata, APISubscriber, APIAccessLog, SignalDelivery
)
from .signal_service import SignalGenerator, SignalManager
from .scrapers import ScrapingManager
from .gpt_service import GPTNewsAnalyzer

logger = logging.getLogger(__name__)

def index(request):
    """Main dashboard view"""
    # Get recent articles
    recent_articles = NewsArticle.objects.all()[:10]
    
    # Get scraping statistics
    total_articles = NewsArticle.objects.count()
    total_sessions = ScrapingSession.objects.count()
    recent_sessions = ScrapingSession.objects.all()[:5]
    
    # Get sentiment distribution
    sentiment_stats = NewsArticle.objects.exclude(gpt_sentiment__isnull=True).values('gpt_sentiment').annotate(count=Count('id'))
    
    # Get impact distribution
    impact_stats = NewsArticle.objects.exclude(gpt_impact__isnull=True).values('gpt_impact').annotate(count=Count('id'))
    
    # Get articles by source
    articles_by_source = {}
    source_counts = NewsArticle.objects.values('source').annotate(count=Count('id'))
    for source_count in source_counts:
        articles_by_source[source_count['source']] = source_count['count']
    
    # Get recent trading recommendations
    recent_recommendations = TradingRecommendation.objects.all()[:5]
    
    # Get analysis statistics
    analyzed_articles = NewsArticle.objects.exclude(gpt_sentiment__isnull=True).count()
    analysis_percentage = (analyzed_articles / total_articles * 100) if total_articles > 0 else 0
    
    # Get latest scraping activity
    latest_scraping = ScrapingSession.objects.filter(status='completed').order_by('-end_time')[:3]
    
    context = {
        'recent_articles': recent_articles,
        'total_articles': total_articles,
        'total_sessions': total_sessions,
        'recent_sessions': recent_sessions,
        'sentiment_stats': sentiment_stats,
        'impact_stats': impact_stats,
        'articles_by_source': articles_by_source,
        'recent_recommendations': recent_recommendations,
        'analyzed_articles': analyzed_articles,
        'analysis_percentage': round(analysis_percentage, 1),
        'latest_scraping': latest_scraping,
    }
    return render(request, 'home.html', context)

def news_dashboard(request):
    """News dashboard with filtering and analysis"""
    # Get filter parameters
    source_filter = request.GET.get('source', '')
    sentiment_filter = request.GET.get('sentiment', '')
    impact_filter = request.GET.get('impact', '')
    search_query = request.GET.get('search', '')
    
    # Build query
    articles = NewsArticle.objects.all()
    
    if source_filter:
        articles = articles.filter(source=source_filter)
    
    if sentiment_filter:
        articles = articles.filter(gpt_sentiment=sentiment_filter)
    
    if impact_filter:
        articles = articles.filter(gpt_impact=impact_filter)
    
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) | 
            Q(summary__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(articles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    sources = NewsArticle.objects.values_list('source', flat=True).distinct()
    sentiments = NewsArticle.SENTIMENT_CHOICES
    impacts = NewsArticle.IMPACT_CHOICES
    
    context = {
        'page_obj': page_obj,
        'sources': sources,
        'sentiments': sentiments,
        'impacts': impacts,
        'current_filters': {
            'source': source_filter,
            'sentiment': sentiment_filter,
            'impact': impact_filter,
            'search': search_query,
        }
    }
    return render(request, 'news_dashboard.html', context)

def scraping_control(request):
    """Scraping control panel"""
    # Get recent scraping sessions
    recent_sessions = ScrapingSession.objects.all()[:10]
    
    # Get total articles count
    total_articles = NewsArticle.objects.count()
    
    # Get article counts by source
    articles_by_source = {}
    source_counts = NewsArticle.objects.values('source').annotate(count=Count('id'))
    
    for source_count in source_counts:
        articles_by_source[source_count['source']] = source_count['count']
    
    # Get recent articles
    recent_articles = NewsArticle.objects.all()[:5]
    
    context = {
        'recent_sessions': recent_sessions,
        'total_articles': total_articles,
        'articles_by_source': articles_by_source,
        'recent_articles': recent_articles,
    }
    return render(request, 'scraping_control.html', context)

def api_config(request):
    """API configuration management"""
    if request.method == 'POST':
        name = request.POST.get('name')
        api_key = request.POST.get('api_key')
        base_url = request.POST.get('base_url')
        
        if name and api_key:
            APIConfig.objects.create(
                name=name,
                api_key=api_key,
                base_url=base_url or ''
            )
            messages.success(request, 'API configuration added successfully!')
            return redirect('api_config')
    
    configs = APIConfig.objects.all()
    context = {'configs': configs}
    return render(request, 'api_config.html', context)

def api_documentation(request):
    """API documentation and endpoints overview"""
    api_endpoints = [
        {
            'name': 'Start Scraping',
            'url': '/api/start-scraping/',
            'method': 'POST',
            'description': 'Start scraping news from selected sources',
            'parameters': {
                'source': 'Data source (reuters, bloomberg, yahoo_finance, marketwatch, cnbc, all)',
                'max_articles': 'Maximum number of articles to scrape (1-100)'
            },
            'example': {
                'source': 'reuters',
                'max_articles': 20
            }
        },
        {
            'name': 'Analyze Article',
            'url': '/api/analyze-article/<article_id>/',
            'method': 'POST',
            'description': 'Analyze a single article using GPT for sentiment and impact',
            'parameters': {
                'article_id': 'ID of the article to analyze'
            },
            'example': '/api/analyze-article/1/'
        },
        {
            'name': 'Batch Analyze Articles',
            'url': '/api/batch-analyze/',
            'method': 'POST',
            'description': 'Analyze multiple articles in batch using GPT',
            'parameters': {
                'article_ids': 'List of article IDs (optional)',
                'limit': 'Maximum number of articles to analyze (default: 10)'
            },
            'example': {
                'limit': 15,
                'article_ids': [1, 2, 3, 4, 5]
            }
        },
        {
            'name': 'Generate Trading Recommendation',
            'url': '/api/generate-recommendation/',
            'method': 'POST',
            'description': 'Generate AI-powered trading recommendation for a ticker',
            'parameters': {
                'ticker': 'Stock ticker symbol (e.g., AAPL, TSLA, MSFT)'
            },
            'example': {
                'ticker': 'AAPL'
            }
        }
    ]
    
    context = {
        'api_endpoints': api_endpoints,
        'base_url': request.build_absolute_uri('/')[:-1],  # Remove trailing slash
    }
    return render(request, 'api_documentation.html', context)

@csrf_exempt
def test_scraping_api(request):
    """Simple test endpoint to verify API is working"""
    if request.method == 'GET':
        return JsonResponse({'status': 'API is working', 'message': 'Test endpoint reached successfully'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def home_stats(request):
    """API endpoint to get home page statistics"""
    try:
        # Get basic statistics
        total_articles = NewsArticle.objects.count()
        total_sessions = ScrapingSession.objects.count()
        analyzed_articles = NewsArticle.objects.exclude(gpt_sentiment__isnull=True).count()
        analysis_percentage = (analyzed_articles / total_articles * 100) if total_articles > 0 else 0
        
        # Get recent activity
        recent_articles = NewsArticle.objects.all()[:5]
        latest_scraping = ScrapingSession.objects.filter(status='completed').order_by('-end_time')[:3]
        
        return JsonResponse({
            'success': True,
            'total_articles': total_articles,
            'total_sessions': total_sessions,
            'analyzed_articles': analyzed_articles,
            'analysis_percentage': round(analysis_percentage, 1),
            'recent_articles_count': len(recent_articles),
            'latest_scraping_count': len(latest_scraping)
        })
        
    except Exception as e:
        logger.error(f"Error in home_stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def start_scraping(request):
    """API endpoint to start scraping"""
    try:
        logger.info("Starting scraping request...")
        
        # Parse request data
        data = json.loads(request.body)
        source = data.get('source', 'reuters')
        max_articles = int(data.get('max_articles', 20))
        
        logger.info(f"Scraping request: source={source}, max_articles={max_articles}")
        
        # Initialize scraping manager
        manager = ScrapingManager()
        logger.info("ScrapingManager initialized successfully")
        
        # Start scraping based on source
        articles = []
        if source == 'reuters':
            logger.info("Starting Reuters scraping...")
            articles = manager.scrape_reuters(max_articles, save_to_db=True)
        elif source == 'bloomberg':
            logger.info("Starting Bloomberg scraping...")
            articles = manager.scrape_bloomberg(max_articles, save_to_db=True)
        elif source == 'yahoo_finance':
            logger.info("Starting Yahoo Finance scraping...")
            articles = manager.scrape_yahoo_finance(max_articles, save_to_db=True)
        elif source == 'marketwatch':
            logger.info("Starting MarketWatch scraping...")
            articles = manager.scrape_marketwatch(max_articles, save_to_db=True)
        elif source == 'cnbc':
            logger.info("Starting CNBC scraping...")
            articles = manager.scrape_cnbc(max_articles, save_to_db=True)
        elif source == 'all':
            logger.info("Starting scraping from all sources...")
            # Scrape all sources
            all_articles = []
            all_articles.extend(manager.scrape_reuters(max_articles, save_to_db=True))
            all_articles.extend(manager.scrape_bloomberg(max_articles, save_to_db=True))
            all_articles.extend(manager.scrape_yahoo_finance(max_articles, save_to_db=True))
            all_articles.extend(manager.scrape_marketwatch(max_articles, save_to_db=True))
            all_articles.extend(manager.scrape_cnbc(max_articles, save_to_db=True))
            articles = all_articles
        else:
            logger.error(f"Invalid source: {source}")
            return JsonResponse({'error': f'Invalid source: {source}'}, status=400)
        
        logger.info(f"Scraping completed. Articles found: {len(articles)}")
        
        return JsonResponse({
            'success': True,
            'message': f'Scraped {len(articles)} articles from {source}',
            'articles_count': len(articles)
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return JsonResponse({'error': 'Invalid max_articles value'}, status=400)
    except Exception as e:
        logger.error(f"Error in start_scraping: {e}")
        return JsonResponse({'error': f'Scraping failed: {str(e)}'}, status=500)

def news_analysis(request):
    """News analysis dashboard"""
    # Get articles that haven't been analyzed yet
    unanalyzed_articles = NewsArticle.objects.filter(
        Q(gpt_sentiment__isnull=True) | Q(gpt_impact__isnull=True)
    )[:50]
    
    # Get analyzed articles count
    analyzed_articles_count = NewsArticle.objects.exclude(
        Q(gpt_sentiment__isnull=True) & Q(gpt_impact__isnull=True)
    ).count()
    
    # Get recently analyzed articles for display
    recently_analyzed_articles = NewsArticle.objects.exclude(
        Q(gpt_sentiment__isnull=True) & Q(gpt_impact__isnull=True)
    ).order_by('-gpt_analysis_date')[:20]
    
    # Get sentiment distribution
    sentiment_distribution = NewsArticle.objects.exclude(
        gpt_sentiment__isnull=True
    ).values('gpt_sentiment').annotate(count=Count('id'))
    
    # Get impact distribution
    impact_distribution = NewsArticle.objects.exclude(
        gpt_impact__isnull=True
    ).values('gpt_impact').annotate(count=Count('id'))
    
    context = {
        'unanalyzed_articles': unanalyzed_articles,
        'analyzed_articles_count': analyzed_articles_count,
        'recently_analyzed_articles': recently_analyzed_articles,
        'sentiment_distribution': sentiment_distribution,
        'impact_distribution': impact_distribution,
    }
    return render(request, 'news_analysis.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def analyze_article(request, article_id):
    """API endpoint to analyze a single article"""
    try:
        article = get_object_or_404(NewsArticle, id=article_id)
        
        # Initialize GPT analyzer
        gpt_analyzer = GPTNewsAnalyzer()
        
        # Analyze sentiment
        sentiment_result = gpt_analyzer.analyze_article_sentiment(article)
        
        # Analyze impact
        impact_result = gpt_analyzer.classify_news_impact(article)
        
        # Update article with analysis results
        article.gpt_sentiment = sentiment_result.get('sentiment')
        article.gpt_sentiment_confidence = sentiment_result.get('confidence')
        article.gpt_sentiment_reason = sentiment_result.get('reason', '')
        article.gpt_impact = impact_result.get('impact')
        article.gpt_impact_confidence = impact_result.get('confidence')
        article.gpt_sectors = impact_result.get('sectors', [])
        article.gpt_analysis_date = timezone.now()
        article.gpt_model_used = sentiment_result.get('model', 'gpt-3.5-turbo')
        article.save()
        
        return JsonResponse({
            'success': True,
            'sentiment': sentiment_result,
            'impact': impact_result,
            'message': f'Article {article.title[:50]}... analyzed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error analyzing article {article_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def batch_analyze_articles(request):
    """API endpoint to analyze multiple articles"""
    try:
        data = json.loads(request.body)
        article_ids = data.get('article_ids', [])
        limit = data.get('limit', 10)
        
        if not article_ids:
            # Get unanalyzed articles
            articles = NewsArticle.objects.filter(
                Q(gpt_sentiment__isnull=True) | Q(gpt_impact__isnull=True)
            )[:limit]
        else:
            articles = NewsArticle.objects.filter(id__in=article_ids[:limit])
        
        # Initialize GPT analyzer
        gpt_analyzer = GPTNewsAnalyzer()
        
        # Batch analyze articles
        results = gpt_analyzer.batch_analyze_articles(articles)
        
        # Update articles with results
        updated_count = 0
        for result in results:
            try:
                article = NewsArticle.objects.get(id=result['article_id'])
                
                sentiment = result['sentiment']
                impact = result['impact']
                
                article.gpt_sentiment = sentiment.get('sentiment')
                article.gpt_sentiment_confidence = sentiment.get('confidence')
                article.gpt_sentiment_reason = sentiment.get('reason', '')
                article.gpt_impact = impact.get('impact')
                article.gpt_impact_confidence = impact.get('confidence')
                article.gpt_sectors = impact.get('sectors', [])
                article.gpt_analysis_date = timezone.now()
                article.gpt_model_used = sentiment.get('model', 'gpt-3.5-turbo')
                article.save()
                
                updated_count += 1
                
            except NewsArticle.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'articles_analyzed': updated_count,
            'total_articles': len(articles),
            'message': f'Successfully analyzed {updated_count} articles'
        })
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def trading_recommendations(request):
    """Trading recommendations dashboard"""
    # Get filter parameters
    ticker_filter = request.GET.get('ticker', '')
    action_filter = request.GET.get('action', '')
    confidence_min = request.GET.get('confidence_min', '')
    
    # Build query
    recommendations = TradingRecommendation.objects.all()
    
    if ticker_filter:
        recommendations = recommendations.filter(ticker__icontains=ticker_filter)
    
    if action_filter:
        recommendations = recommendations.filter(action=action_filter)
    
    if confidence_min:
        try:
            confidence_min = float(confidence_min)
            recommendations = recommendations.filter(confidence__gte=confidence_min)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(recommendations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_recommendations = TradingRecommendation.objects.count()
    action_distribution = TradingRecommendation.objects.values('action').annotate(count=Count('id'))
    
    context = {
        'page_obj': page_obj,
        'total_recommendations': total_recommendations,
        'action_distribution': action_distribution,
        'current_filters': {
            'ticker': ticker_filter,
            'action': action_filter,
            'confidence_min': confidence_min,
        }
    }
    return render(request, 'trading_recommendations.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def generate_trading_recommendation(request):
    """API endpoint to generate trading recommendation for a ticker"""
    try:
        data = json.loads(request.body)
        ticker = data.get('ticker', '').upper()
        
        if not ticker:
            return JsonResponse({'error': 'Ticker is required'}, status=400)
        
        # Get recent articles related to the ticker
        related_articles = NewsArticle.objects.filter(
            Q(title__icontains=ticker) | 
            Q(summary__icontains=ticker)
        ).order_by('-published_date', '-created_at')[:10]
        
        if not related_articles:
            return JsonResponse({
                'error': f'No articles found for ticker {ticker}',
                'suggestion': 'Try scraping news first or check if the ticker is mentioned in existing articles'
            }, status=404)
        
        # Initialize GPT analyzer
        gpt_analyzer = GPTNewsAnalyzer()
        
        # Generate trading recommendation
        recommendation_result = gpt_analyzer.generate_trading_recommendation(ticker, related_articles)
        
        # Create trading recommendation record
        trading_rec = TradingRecommendation.objects.create(
            ticker=ticker,
            action=recommendation_result.get('action', 'hold'),
            confidence=recommendation_result.get('confidence', 0.5),
            reason=recommendation_result.get('reason', ''),
            timeframe=recommendation_result.get('timeframe', 'medium'),
            gpt_model_used=recommendation_result.get('model', 'gpt-3.5-turbo'),
            articles_analyzed=len(related_articles)
        )
        
        # Add related articles
        trading_rec.related_articles.set(related_articles)
        
        return JsonResponse({
            'success': True,
            'recommendation': {
                'id': trading_rec.id,
                'ticker': trading_rec.ticker,
                'action': trading_rec.action,
                'confidence': trading_rec.confidence,
                'reason': trading_rec.reason,
                'timeframe': trading_rec.timeframe,
                'risk_level': trading_rec.get_risk_level(),
                'articles_analyzed': trading_rec.articles_analyzed
            },
            'message': f'Trading recommendation generated for {ticker}'
        })
        
    except Exception as e:
        logger.error(f"Error generating trading recommendation: {e}")
        return JsonResponse({'error': str(e)}, status=500)

def gpt_analytics(request):
    """GPT analytics and monitoring dashboard"""
    # Initialize GPT analyzer to get stats
    gpt_analyzer = GPTNewsAnalyzer()
    token_stats = gpt_analyzer.get_token_usage_stats()
    
    # Get analysis statistics
    total_articles = NewsArticle.objects.count()
    analyzed_articles_count = NewsArticle.objects.exclude(
        Q(gpt_sentiment__isnull=True) & Q(gpt_impact__isnull=True)
    ).count()
    
    # Get model usage statistics
    model_usage = NewsArticle.objects.exclude(
        gpt_model_used__isnull=True
    ).values('gpt_model_used').annotate(count=Count('id'))
    
    # Get recent analysis activity
    recent_analysis = NewsArticle.objects.exclude(
        gpt_analysis_date__isnull=True
    ).order_by('-gpt_analysis_date')[:10]
    
    context = {
        'token_stats': token_stats,
        'total_articles': total_articles,
        'analyzed_articles_count': analyzed_articles_count,
        'analysis_percentage': (analyzed_articles_count / total_articles * 100) if total_articles > 0 else 0,
        'model_usage': model_usage,
        'recent_analysis': recent_analysis,
    }
    return render(request, 'gpt_analytics.html', context)



# Market Data Views

def market_data_dashboard(request):
    """Market data dashboard"""
    # Get market data statistics
    total_tickers = MarketTicker.objects.count()
    active_tickers = MarketTicker.objects.filter(is_active=True).count()
    total_market_data = MarketData.objects.count()
    total_historical_data = HistoricalData.objects.count()
    
    # Get recent market data
    recent_market_data = MarketData.objects.select_related('ticker').order_by('-timestamp')[:10]
    
    # Get active connections
    active_connections = IBConnection.objects.filter(is_active=True)
    
    # Get recent data collection jobs
    recent_jobs = DataCollectionJob.objects.order_by('-created_at')[:5]
    
    # Get top movers (if we have data)
    top_movers = MarketData.objects.filter(
        price_change_percent__isnull=False
    ).select_related('ticker').order_by('-price_change_percent')[:5]
    
    context = {
        'total_tickers': total_tickers,
        'active_tickers': active_tickers,
        'total_market_data': total_market_data,
        'total_historical_data': total_historical_data,
        'recent_market_data': recent_market_data,
        'active_connections': active_connections,
        'recent_jobs': recent_jobs,
        'top_movers': top_movers,
    }
    return render(request, 'market_data_dashboard.html', context)

def ticker_list(request):
    """List all tickers with filtering"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    sector_filter = request.GET.get('sector', '')
    exchange_filter = request.GET.get('exchange', '')
    active_filter = request.GET.get('active', '')
    
    # Build query
    tickers = MarketTicker.objects.all()
    
    if search_query:
        tickers = tickers.filter(
            Q(symbol__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )
    
    if sector_filter:
        tickers = tickers.filter(sector=sector_filter)
    
    if exchange_filter:
        tickers = tickers.filter(exchange=exchange_filter)
    
    if active_filter == 'true':
        tickers = tickers.filter(is_active=True)
    elif active_filter == 'false':
        tickers = tickers.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(tickers, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    sectors = MarketTicker.objects.values_list('sector', flat=True).distinct().exclude(sector__isnull=True)
    exchanges = MarketTicker.objects.values_list('exchange', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'sectors': sectors,
        'exchanges': exchanges,
        'current_filters': {
            'search': search_query,
            'sector': sector_filter,
            'exchange': exchange_filter,
            'active': active_filter,
        }
    }
    return render(request, 'ticker_list.html', context)

def ticker_detail(request, ticker_id):
    """Detailed view for a specific ticker"""
    ticker = get_object_or_404(MarketTicker, id=ticker_id)
    
    # Get latest market data
    latest_market_data = MarketData.objects.filter(ticker=ticker).order_by('-timestamp').first()
    
    # Get recent market data (last 24 hours)
    recent_market_data = MarketData.objects.filter(
        ticker=ticker,
        timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
    ).order_by('-timestamp')[:20]
    
    # Get historical data (last 30 days)
    historical_data = HistoricalData.objects.filter(
        ticker=ticker,
        bar_time__gte=timezone.now() - timezone.timedelta(days=30)
    ).order_by('-bar_time')[:30]
    
    # Get related news articles
    related_articles = NewsArticle.objects.filter(
        Q(title__icontains=ticker.symbol) |
        Q(summary__icontains=ticker.symbol) |
        Q(content__icontains=ticker.symbol)
    ).order_by('-published_date')[:10]
    
    context = {
        'ticker': ticker,
        'latest_market_data': latest_market_data,
        'recent_market_data': recent_market_data,
        'historical_data': historical_data,
        'related_articles': related_articles,
    }
    return render(request, 'ticker_detail.html', context)

def ib_connections(request):
    """IB connections management"""
    if request.method == 'POST':
        name = request.POST.get('name')
        host = request.POST.get('host')
        port = request.POST.get('port')
        client_id = request.POST.get('client_id')
        
        if name and host and port:
            try:
                # Check if connection with this name already exists
                if IBConnection.objects.filter(name=name).exists():
                    messages.error(request, f'Connection with name "{name}" already exists. Please choose a different name.')
                else:
                    IBConnection.objects.create(
                        name=name,
                        host=host,
                        port=int(port),
                        client_id=int(client_id) if client_id else 1
                    )
                    messages.success(request, 'IB connection added successfully!')
            except Exception as e:
                messages.error(request, f'Error creating connection: {str(e)}')
            
            return redirect('ib_connections')
        else:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('ib_connections')
    
    connections = IBConnection.objects.all()
    context = {'connections': connections}
    return render(request, 'ib_connections.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def ib_connection_connect(request):
    """API endpoint to connect to IB"""
    try:
        data = json.loads(request.body)
        connection_name = data.get('connection_name')
        
        if not connection_name:
            return JsonResponse({'success': False, 'error': 'Connection name is required'}, status=400)
        
        try:
            connection = IBConnection.objects.get(name=connection_name)
            # TODO: Implement actual IB connection logic here
            # For now, just simulate a successful connection
            connection.status = 'connected'
            connection.last_connected = timezone.now()
            connection.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully connected to {connection_name}'
            })
        except IBConnection.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Connection not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ib_connection_disconnect(request):
    """API endpoint to disconnect from IB"""
    try:
        data = json.loads(request.body)
        connection_name = data.get('connection_name')
        
        if not connection_name:
            return JsonResponse({'success': False, 'error': 'Connection name is required'}, status=400)
        
        try:
            connection = IBConnection.objects.get(name=connection_name)
            # TODO: Implement actual IB disconnection logic here
            # For now, just simulate a successful disconnection
            connection.status = 'disconnected'
            connection.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully disconnected from {connection_name}'
            })
        except IBConnection.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Connection not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ib_connection_test(request):
    """API endpoint to test IB connection"""
    try:
        data = json.loads(request.body)
        connection_name = data.get('connection_name')
        
        if not connection_name:
            return JsonResponse({'success': False, 'error': 'Connection name is required'}, status=400)
        
        try:
            connection = IBConnection.objects.get(name=connection_name)
            # TODO: Implement actual IB connection test logic here
            # For now, just simulate a successful test
            return JsonResponse({
                'success': True,
                'message': f'Connection test successful for {connection_name}',
                'connection_info': {
                    'name': connection.name,
                    'host': connection.host,
                    'port': connection.port,
                    'client_id': connection.client_id
                }
            })
        except IBConnection.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Connection not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ib_connection_delete(request):
    """API endpoint to delete IB connection"""
    try:
        data = json.loads(request.body)
        connection_name = data.get('connection_name')
        
        if not connection_name:
            return JsonResponse({'success': False, 'error': 'Connection name is required'}, status=400)
        
        try:
            connection = IBConnection.objects.get(name=connection_name)
            connection.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully deleted connection {connection_name}'
            })
        except IBConnection.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Connection not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def start_market_data_collection(request):
    """API endpoint to start market data collection"""
    try:
        data = json.loads(request.body)
        tickers = data.get('tickers', [])
        data_type = data.get('type', 'both')  # realtime, historical, both
        connection_name = data.get('connection', None)
        
        if not tickers:
            return JsonResponse({'error': 'No tickers provided'}, status=400)
        
        # Create data collection job
        job = DataCollectionJob.objects.create(
            job_type='realtime' if data_type == 'realtime' else 'historical',
            tickers=tickers,
            total_items=len(tickers),
            status='pending'
        )
        
        # TODO: Start actual data collection in background
        # This would typically use Celery or similar task queue
        
        return JsonResponse({
            'success': True,
            'job_id': job.id,
            'message': f'Market data collection job created for {len(tickers)} tickers'
        })
        
    except Exception as e:
        logger.error(f"Error starting market data collection: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def market_data_stats(request):
    """API endpoint to get market data statistics"""
    try:
        # Get basic statistics
        total_tickers = MarketTicker.objects.count()
        active_tickers = MarketTicker.objects.filter(is_active=True).count()
        total_market_data = MarketData.objects.count()
        total_historical_data = HistoricalData.objects.count()
        
        # Get recent activity
        recent_market_data = MarketData.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
        ).count()
        
        # Get active connections
        active_connections = IBConnection.objects.filter(is_active=True).count()
        
        # Get recent jobs
        recent_jobs = DataCollectionJob.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
        
        return JsonResponse({
            'success': True,
            'total_tickers': total_tickers,
            'active_tickers': active_tickers,
            'total_market_data': total_market_data,
            'total_historical_data': total_historical_data,
            'recent_market_data': recent_market_data,
            'active_connections': active_connections,
            'recent_jobs': recent_jobs,
        })
        
    except Exception as e:
        logger.error(f"Error getting market data stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# Signal Management Views

def signal_dashboard(request):
    """Signal dashboard view"""
    try:
        # Get signal statistics
        total_signals = TradingSignal.objects.count()
        active_signals = TradingSignal.objects.filter(status='active').count()
        executed_signals = TradingSignal.objects.filter(status='executed').count()
        
        # Get recent signals
        recent_signals = TradingSignal.objects.select_related('ticker').order_by('-timestamp')[:10]
        
        # Get signals by type
        signals_by_type = {}
        for signal_type, _ in TradingSignal.SIGNAL_TYPE_CHOICES:
            count = TradingSignal.objects.filter(signal_type=signal_type, status='active').count()
            signals_by_type[signal_type] = count
        
        # Get top performing signals
        top_signals = TradingSignal.objects.filter(
            status='executed',
            performance_score__isnull=False
        ).order_by('-performance_score')[:5]
        
        # Get performance stats
        performance_stats = SignalManager.get_signal_performance_stats()
        
        context = {
            'total_signals': total_signals,
            'active_signals': active_signals,
            'executed_signals': executed_signals,
            'recent_signals': recent_signals,
            'signals_by_type': signals_by_type,
            'top_signals': top_signals,
            'performance_stats': performance_stats,
        }
        
        return render(request, 'signal_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in signal dashboard: {e}")
        return render(request, 'signal_dashboard.html', {'error': str(e)})

def signal_list(request):
    """Signal list view with filtering and pagination"""
    try:
        # Get filter parameters
        signal_type = request.GET.get('type', '')
        status = request.GET.get('status', '')
        ticker = request.GET.get('ticker', '')
        min_confidence = request.GET.get('min_confidence', '')
        
        # Build queryset
        signals = TradingSignal.objects.select_related('ticker').all()
        
        if signal_type:
            signals = signals.filter(signal_type=signal_type)
        
        if status:
            signals = signals.filter(status=status)
        
        if ticker:
            signals = signals.filter(ticker__symbol__icontains=ticker)
        
        if min_confidence:
            try:
                min_conf = float(min_confidence)
                signals = signals.filter(confidence__gte=min_conf)
            except ValueError:
                pass
        
        # Order by timestamp
        signals = signals.order_by('-timestamp')
        
        # Pagination
        paginator = Paginator(signals, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get filter options
        signal_types = TradingSignal.SIGNAL_TYPE_CHOICES
        status_choices = TradingSignal.SIGNAL_STATUS_CHOICES
        tickers = MarketTicker.objects.filter(is_active=True).order_by('symbol')
        
        context = {
            'page_obj': page_obj,
            'signal_types': signal_types,
            'status_choices': status_choices,
            'tickers': tickers,
            'current_filters': {
                'type': signal_type,
                'status': status,
                'ticker': ticker,
                'min_confidence': min_confidence,
            }
        }
        
        return render(request, 'signal_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in signal list: {e}")
        return render(request, 'signal_list.html', {'error': str(e)})

def signal_detail(request, signal_id):
    """Signal detail view"""
    try:
        signal = get_object_or_404(TradingSignal, id=signal_id)
        
        # Get related data
        related_articles = signal.related_articles.all()
        metadata = getattr(signal, 'metadata', None)
        
        # Get recent market data for the ticker
        recent_market_data = MarketData.objects.filter(
            ticker=signal.ticker
        ).order_by('-timestamp')[:10]
        
        # Get historical signals for the same ticker
        historical_signals = TradingSignal.objects.filter(
            ticker=signal.ticker
        ).exclude(id=signal_id).order_by('-timestamp')[:5]
        
        context = {
            'signal': signal,
            'related_articles': related_articles,
            'metadata': metadata,
            'recent_market_data': recent_market_data,
            'historical_signals': historical_signals,
        }
        
        return render(request, 'signal_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in signal detail: {e}")
        return render(request, 'signal_detail.html', {'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def generate_signal_api(request):
    """API endpoint to generate a signal"""
    try:
        data = json.loads(request.body)
        ticker_symbol = data.get('ticker')
        source = data.get('source', 'combined')
        
        if not ticker_symbol:
            return JsonResponse({'error': 'Ticker symbol is required'}, status=400)
        
        # Generate signal
        signal_generator = SignalGenerator()
        signal = signal_generator.generate_signal(ticker_symbol, source)
        
        if signal:
            return JsonResponse({
                'success': True,
                'signal_id': signal.id,
                'ticker': signal.ticker.symbol,
                'signal_type': signal.signal_type,
                'confidence': signal.confidence,
                'timestamp': signal.timestamp.isoformat(),
                'message': f'Signal generated for {ticker_symbol}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Could not generate signal for {ticker_symbol}'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def execute_signal_api(request):
    """API endpoint to execute a signal"""
    try:
        data = json.loads(request.body)
        signal_id = data.get('signal_id')
        execution_price = data.get('execution_price')
        
        if not signal_id or not execution_price:
            return JsonResponse({'error': 'Signal ID and execution price are required'}, status=400)
        
        try:
            signal = TradingSignal.objects.get(id=signal_id)
        except TradingSignal.DoesNotExist:
            return JsonResponse({'error': 'Signal not found'}, status=404)
        
        if signal.status != 'active':
            return JsonResponse({'error': 'Signal is not active'}, status=400)
        
        # Update signal
        signal.status = 'executed'
        signal.execution_price = execution_price
        signal.execution_time = timezone.now()
        signal.save()
        
        # Calculate performance
        performance = signal.calculate_performance()
        
        return JsonResponse({
            'success': True,
            'signal_id': signal.id,
            'execution_price': float(signal.execution_price),
            'execution_time': signal.execution_time.isoformat(),
            'performance_score': performance,
            'message': f'Signal executed for {signal.ticker.symbol}'
        })
        
    except Exception as e:
        logger.error(f"Error executing signal: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def signal_stats_api(request):
    """API endpoint to get signal statistics"""
    try:
        # Get basic stats
        total_signals = TradingSignal.objects.count()
        active_signals = TradingSignal.objects.filter(status='active').count()
        executed_signals = TradingSignal.objects.filter(status='executed').count()
        expired_signals = TradingSignal.objects.filter(status='expired').count()
        
        # Get signals by type
        signals_by_type = {}
        for signal_type, _ in TradingSignal.SIGNAL_TYPE_CHOICES:
            count = TradingSignal.objects.filter(signal_type=signal_type).count()
            signals_by_type[signal_type] = count
        
        # Get performance stats
        performance_stats = SignalManager.get_signal_performance_stats()
        
        # Get recent signals
        recent_signals = TradingSignal.objects.select_related('ticker').order_by('-timestamp')[:5]
        recent_signals_data = [
            {
                'id': s.id,
                'ticker': s.ticker.symbol,
                'signal_type': s.signal_type,
                'confidence': s.confidence,
                'timestamp': s.timestamp.isoformat(),
                'status': s.status
            }
            for s in recent_signals
        ]
        
        return JsonResponse({
            'success': True,
            'total_signals': total_signals,
            'active_signals': active_signals,
            'executed_signals': executed_signals,
            'expired_signals': expired_signals,
            'signals_by_type': signals_by_type,
            'performance_stats': performance_stats,
            'recent_signals': recent_signals_data
        })
        
    except Exception as e:
        logger.error(f"Error getting signal stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# API Subscriber Management Views
def api_subscribers(request):
    """View for managing API subscribers"""
    subscribers = APISubscriber.objects.all().order_by('-created_at')
    
    context = {
        'subscribers': subscribers,
    }
    return render(request, 'api_subscribers.html', context)


@require_http_methods(["POST"])
def add_api_subscriber(request):
    """Add a new API subscriber"""
    try:
        name = request.POST.get('name')
        email = request.POST.get('email')
        description = request.POST.get('description', '')
        webhook_url = request.POST.get('webhook_url', '')
        rate_limit = int(request.POST.get('rate_limit', 1000))
        
        if not name or not email:
            messages.error(request, 'Name and email are required')
            return redirect('api_subscribers')
        
        # Check if subscriber already exists
        if APISubscriber.objects.filter(name=name).exists():
            messages.error(request, f'Subscriber with name "{name}" already exists')
            return redirect('api_subscribers')
        
        if APISubscriber.objects.filter(contact_email=email).exists():
            messages.error(request, f'Subscriber with email "{email}" already exists')
            return redirect('api_subscribers')
        
        # Create subscriber
        subscriber = APISubscriber(
            name=name,
            contact_email=email,
            description=description,
            webhook_url=webhook_url,
            rate_limit_per_hour=rate_limit,
            status='active'
        )
        subscriber.save()
        
        messages.success(request, f'Successfully created API subscriber: {name}')
        messages.info(request, f'API Key: {subscriber.api_key}')
        
    except Exception as e:
        logger.error(f"Error creating API subscriber: {e}")
        messages.error(request, f'Error creating subscriber: {str(e)}')
    
    return redirect('api_subscribers')


def api_subscriber_detail(request, subscriber_id):
    """View detailed information about an API subscriber"""
    subscriber = get_object_or_404(APISubscriber, id=subscriber_id)
    
    # Get recent access logs
    access_logs = APIAccessLog.objects.filter(subscriber=subscriber).order_by('-timestamp')[:20]
    
    # Get delivery stats
    delivery_stats = {
        'total_deliveries': SignalDelivery.objects.filter(subscriber=subscriber).count(),
        'delivered': SignalDelivery.objects.filter(subscriber=subscriber, status='delivered').count(),
        'failed': SignalDelivery.objects.filter(subscriber=subscriber, status='failed').count(),
        'pending': SignalDelivery.objects.filter(subscriber=subscriber, status='pending').count(),
    }
    
    if delivery_stats['total_deliveries'] > 0:
        delivery_stats['success_rate'] = (delivery_stats['delivered'] / delivery_stats['total_deliveries']) * 100
    else:
        delivery_stats['success_rate'] = 0
    
    context = {
        'subscriber': subscriber,
        'access_logs': access_logs,
        'delivery_stats': delivery_stats,
    }
    return render(request, 'api_subscriber_detail.html', context)


@require_http_methods(["POST"])
def update_api_subscriber(request, subscriber_id):
    """Update an API subscriber"""
    subscriber = get_object_or_404(APISubscriber, id=subscriber_id)
    
    try:
        subscriber.name = request.POST.get('name', subscriber.name)
        subscriber.contact_email = request.POST.get('email', subscriber.contact_email)
        subscriber.description = request.POST.get('description', subscriber.description)
        subscriber.webhook_url = request.POST.get('webhook_url', subscriber.webhook_url)
        subscriber.rate_limit_per_hour = int(request.POST.get('rate_limit', subscriber.rate_limit_per_hour))
        subscriber.status = request.POST.get('status', subscriber.status)
        
        subscriber.save()
        messages.success(request, f'Successfully updated subscriber: {subscriber.name}')
        
    except Exception as e:
        logger.error(f"Error updating API subscriber: {e}")
        messages.error(request, f'Error updating subscriber: {str(e)}')
    
    return redirect('api_subscriber_detail', subscriber_id=subscriber_id)


@require_http_methods(["POST"])
def delete_api_subscriber(request, subscriber_id):
    """Delete an API subscriber"""
    subscriber = get_object_or_404(APISubscriber, id=subscriber_id)
    
    try:
        name = subscriber.name
        subscriber.delete()
        messages.success(request, f'Successfully deleted subscriber: {name}')
        
    except Exception as e:
        logger.error(f"Error deleting API subscriber: {e}")
        messages.error(request, f'Error deleting subscriber: {str(e)}')
    
    return redirect('api_subscribers')


@require_http_methods(["POST"])
def regenerate_api_key(request, subscriber_id):
    """Regenerate API key for a subscriber"""
    subscriber = get_object_or_404(APISubscriber, id=subscriber_id)
    
    try:
        old_key = subscriber.api_key
        subscriber.api_key = APISubscriber.generate_api_key()
        subscriber.secret_key = APISubscriber.generate_secret_key()
        subscriber.save()
        
        messages.success(request, f'Successfully regenerated API key for {subscriber.name}')
        messages.info(request, f'New API Key: {subscriber.api_key}')
        
    except Exception as e:
        logger.error(f"Error regenerating API key: {e}")
        messages.error(request, f'Error regenerating API key: {str(e)}')
    
    return redirect('api_subscriber_detail', subscriber_id=subscriber_id)
