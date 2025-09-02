from django.urls import path
from . import views, api_views

urlpatterns = [
    path('', views.index, name='index'),
    path('news/', views.news_dashboard, name='news_dashboard'),
    path('scraping/', views.scraping_control, name='scraping_control'),
    path('api-config/', views.api_config, name='api_config'),
    
    # Main API endpoint
    path('api/', views.api_documentation, name='api_documentation'),
    
    # API endpoints
    path('api/test-scraping/', views.test_scraping_api, name='test_scraping_api'),
    path('api/home-stats/', views.home_stats, name='home_stats'),
    path('api/start-scraping/', views.start_scraping, name='start_scraping'),
    path('api/analyze-article/<int:article_id>/', views.analyze_article, name='analyze_article'),
    path('api/batch-analyze/', views.batch_analyze_articles, name='batch_analyze_articles'),
    path('api/generate-recommendation/', views.generate_trading_recommendation, name='generate_trading_recommendation'),
    
    # News Analysis URLs
    path('analysis/', views.news_analysis, name='news_analysis'),
    
    # Trading Recommendations URLs
    path('recommendations/', views.trading_recommendations, name='trading_recommendations'),
    
    # GPT Analytics URLs (both /analytics/ and /gpt-analytics/ work)
    path('analytics/', views.gpt_analytics, name='analytics'),
    path('gpt-analytics/', views.gpt_analytics, name='gpt_analytics'),
    

    
    # Market Data URLs
    path('market-data/', views.market_data_dashboard, name='market_data_dashboard'),
    path('tickers/', views.ticker_list, name='ticker_list'),
    path('ticker/<int:ticker_id>/', views.ticker_detail, name='ticker_detail'),
    path('ib-connections/', views.ib_connections, name='ib_connections'),
    
    # Market Data API endpoints
    path('api/market-data/collect/', views.start_market_data_collection, name='start_market_data_collection'),
    path('api/market-data/stats/', views.market_data_stats, name='market_data_stats'),
    
    # IB Connection API endpoints
    path('api/ib-connections/connect/', views.ib_connection_connect, name='ib_connection_connect'),
    path('api/ib-connections/disconnect/', views.ib_connection_disconnect, name='ib_connection_disconnect'),
    path('api/ib-connections/test/', views.ib_connection_test, name='ib_connection_test'),
    path('api/ib-connections/delete/', views.ib_connection_delete, name='ib_connection_delete'),
    
    # Signal Management URLs
    path('signals/', views.signal_dashboard, name='signal_dashboard'),
    path('signals/list/', views.signal_list, name='signal_list'),
    path('signal/<int:signal_id>/', views.signal_detail, name='signal_detail'),
    
    # Signal API endpoints
    path('api/signals/generate/', views.generate_signal_api, name='generate_signal_api'),
    path('api/signals/execute/', views.execute_signal_api, name='execute_signal_api'),
    path('api/signals/stats/', views.signal_stats_api, name='signal_stats_api'),
    
    # External API v1 endpoints
    path('api/v1/signals/', api_views.TradingSignalsAPIView.as_view(), name='api_v1_signals'),
    path('api/v1/subscription/', api_views.SignalSubscriptionAPIView.as_view(), name='api_v1_subscription'),
    path('api/v1/webhook/status/', api_views.WebhookDeliveryStatusView.as_view(), name='api_v1_webhook_status'),
    path('api/v1/status/', api_views.api_status, name='api_v1_status'),
    path('api/v1/docs/', api_views.api_documentation, name='api_v1_docs'),
    
    # API Subscriber Management URLs
    path('api-subscribers/', views.api_subscribers, name='api_subscribers'),
    path('api-subscribers/add/', views.add_api_subscriber, name='add_api_subscriber'),
    path('api-subscribers/<int:subscriber_id>/', views.api_subscriber_detail, name='api_subscriber_detail'),
    path('api-subscribers/<int:subscriber_id>/update/', views.update_api_subscriber, name='update_api_subscriber'),
    path('api-subscribers/<int:subscriber_id>/delete/', views.delete_api_subscriber, name='delete_api_subscriber'),
    path('api-subscribers/<int:subscriber_id>/regenerate-key/', views.regenerate_api_key, name='regenerate_api_key'),
]