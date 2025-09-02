from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import secrets
import string

# Create your models here.

class NewsArticle(models.Model):
    SOURCE_CHOICES = [
        ('reuters', 'Reuters'),
        ('bloomberg', 'Bloomberg'),
        ('yahoo_finance', 'Yahoo Finance'),
        ('marketwatch', 'MarketWatch'),
        ('cnbc', 'CNBC'),
        ('finnhub', 'FinnHub API'),
        ('manual', 'Manual Entry'),
    ]
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    
    IMPACT_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    title = models.CharField(max_length=500)
    content = models.TextField()
    summary = models.TextField(blank=True, null=True)  # Keep existing behavior
    url = models.URLField(max_length=1000, blank=True, null=True)  # Keep existing behavior
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='reuters')  # Keep existing behavior
    published_date = models.DateTimeField(null=True, blank=True)
    author = models.CharField(max_length=100, blank=True, null=True)  # Keep existing behavior
    category = models.CharField(max_length=100, blank=True, null=True)  # Keep existing behavior
    tags = models.JSONField(default=list, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)
    
    # New GPT analysis fields - all optional
    gpt_sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, null=True, blank=True)
    gpt_sentiment_confidence = models.FloatField(null=True, blank=True)
    gpt_sentiment_reason = models.TextField(blank=True, null=True)
    gpt_impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, null=True, blank=True)
    gpt_impact_confidence = models.FloatField(null=True, blank=True)
    gpt_sectors = models.JSONField(default=list, blank=True)
    gpt_analysis_date = models.DateTimeField(null=True, blank=True)
    gpt_model_used = models.CharField(max_length=50, blank=True, null=True)
    
    # Keep existing timestamp field and add new ones
    scraped_date = models.DateTimeField(default=timezone.now)  # Keep existing
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # New, optional
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)  # New, optional
    
    class Meta:
        ordering = ['-published_date', '-scraped_date']  # Keep existing ordering
        indexes = [
            models.Index(fields=['source', 'published_date']),
            models.Index(fields=['gpt_sentiment', 'gpt_impact']),
            models.Index(fields=['category', 'tags']),
        ]
    
    def __str__(self):
        return f"{self.title[:50]}... ({self.source})"
    
    def get_sentiment_display(self):
        """Get sentiment with confidence"""
        if self.gpt_sentiment and self.gpt_sentiment_confidence:
            return f"{self.get_gpt_sentiment_display()} ({self.gpt_sentiment_confidence:.2f})"
        return "Not analyzed"
    
    def get_impact_display(self):
        """Get impact with confidence"""
        if self.gpt_impact and self.gpt_impact_confidence:
            return f"{self.get_gpt_impact_display()} ({self.gpt_impact_confidence:.2f})"
        return "Not analyzed"

class ScrapingSession(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    source = models.CharField(max_length=50)
    start_time = models.DateTimeField(default=timezone.now)  # Keep existing behavior
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    articles_scraped = models.IntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    errors = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.source} - {self.status} ({self.start_time})"

class APIConfig(models.Model):
    name = models.CharField(max_length=100)
    api_key = models.CharField(max_length=500)
    base_url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)  # Provide default
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"

class TradingRecommendation(models.Model):
    ACTION_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
    ]
    
    TIMEFRAME_CHOICES = [
        ('short', 'Short Term (1-7 days)'),
        ('medium', 'Medium Term (1-4 weeks)'),
        ('long', 'Long Term (1-12 months)'),
    ]
    
    ticker = models.CharField(max_length=20, db_index=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    confidence = models.FloatField(help_text="Confidence score from 0.0 to 1.0")
    reason = models.TextField(help_text="Reasoning for the recommendation")
    timeframe = models.CharField(max_length=10, choices=TIMEFRAME_CHOICES)
    
    # GPT analysis details
    gpt_model_used = models.CharField(max_length=50, blank=True, null=True)
    articles_analyzed = models.IntegerField(default=0)
    analysis_date = models.DateTimeField(auto_now_add=True)
    
    # Related articles
    related_articles = models.ManyToManyField(NewsArticle, blank=True, related_name='trading_recommendations')
    
    # User tracking
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-analysis_date']
        indexes = [
            models.Index(fields=['ticker', 'action']),
            models.Index(fields=['confidence', 'timeframe']),
            models.Index(fields=['analysis_date']),
        ]
    
    def __str__(self):
        return f"{self.ticker}: {self.get_action_display()} ({self.confidence:.2f})"
    
    def get_confidence_display(self):
        """Get confidence as percentage"""
        return f"{self.confidence * 100:.1f}%"
    
    def get_risk_level(self):
        """Get risk level based on confidence and action"""
        if self.confidence >= 0.8:
            risk = "Low"
        elif self.confidence >= 0.6:
            risk = "Medium"
        else:
            risk = "High"
        
        if self.action == 'hold':
            risk = "Minimal"
        
        return risk
    
    def get_recommendation_summary(self):
        """Get a summary of the recommendation"""
        return f"{self.get_action_display().upper()} {self.ticker} with {self.get_confidence_display()} confidence for {self.get_timeframe_display()}"

class NewsAnalysis(models.Model):
    """Model to store detailed news analysis results"""
    article = models.OneToOneField(NewsArticle, on_delete=models.CASCADE, related_name='analysis')
    
    # Sentiment analysis
    sentiment_score = models.FloatField(null=True, blank=True)
    sentiment_label = models.CharField(max_length=20, choices=NewsArticle.SENTIMENT_CHOICES, null=True, blank=True)
    sentiment_confidence = models.FloatField(null=True, blank=True)
    sentiment_reason = models.TextField(blank=True, null=True)
    
    # Impact analysis
    impact_score = models.FloatField(null=True, blank=True)
    impact_level = models.CharField(max_length=20, choices=NewsArticle.IMPACT_CHOICES, null=True, blank=True)
    impact_confidence = models.FloatField(null=True, blank=True)
    affected_sectors = models.JSONField(default=list, blank=True)
    affected_companies = models.JSONField(default=list, blank=True)
    
    # Trading implications
    trading_implications = models.TextField(blank=True, null=True)
    potential_moves = models.JSONField(default=list, blank=True)
    
    # Analysis metadata
    analysis_date = models.DateTimeField(auto_now_add=True)
    model_used = models.CharField(max_length=50, blank=True, null=True)
    processing_time = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-analysis_date']
        verbose_name_plural = "News Analyses"
    
    def __str__(self):
        return f"Analysis for {self.article.title[:50]}..."
    
    def get_combined_score(self):
        """Calculate combined sentiment and impact score"""
        if self.sentiment_score is not None and self.impact_score is not None:
            # Weight sentiment more heavily
            return (self.sentiment_score * 0.7) + (self.impact_score * 0.3)
        return None

# Market Data Models for Interactive Brokers Integration

class MarketTicker(models.Model):
    """Model to store ticker information and metadata"""
    
    EXCHANGE_CHOICES = [
        ('SMART', 'SMART'),
        ('NASDAQ', 'NASDAQ'),
        ('NYSE', 'NYSE'),
        ('AMEX', 'AMEX'),
        ('ARCA', 'ARCA'),
        ('BATS', 'BATS'),
        ('IEX', 'IEX'),
        ('OTC', 'OTC'),
    ]
    
    SECURITY_TYPE_CHOICES = [
        ('STK', 'Stock'),
        ('OPT', 'Option'),
        ('FUT', 'Future'),
        ('IND', 'Index'),
        ('FOP', 'Future Option'),
        ('CASH', 'Cash'),
        ('BAG', 'Bag'),
        ('WAR', 'Warrant'),
        ('BOND', 'Bond'),
        ('CMDTY', 'Commodity'),
        ('NEWS', 'News'),
        ('FUND', 'Fund'),
    ]
    
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('JPY', 'Japanese Yen'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
        ('CHF', 'Swiss Franc'),
        ('CNY', 'Chinese Yuan'),
    ]
    
    symbol = models.CharField(max_length=20, db_index=True)
    exchange = models.CharField(max_length=10, choices=EXCHANGE_CHOICES, default='SMART')
    security_type = models.CharField(max_length=10, choices=SECURITY_TYPE_CHOICES, default='STK')
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='USD')
    
    # Company information
    company_name = models.CharField(max_length=200, blank=True, null=True)
    sector = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    market_cap = models.BigIntegerField(null=True, blank=True)
    
    # Trading information
    is_active = models.BooleanField(default=True)
    is_tradable = models.BooleanField(default=True)
    min_tick = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    lot_size = models.IntegerField(default=1)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_price_update = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['symbol', 'exchange', 'security_type', 'currency']
        indexes = [
            models.Index(fields=['symbol', 'exchange']),
            models.Index(fields=['sector', 'industry']),
            models.Index(fields=['is_active', 'is_tradable']),
        ]
        ordering = ['symbol']
    
    def __str__(self):
        return f"{self.symbol} ({self.exchange})"
    
    def get_full_symbol(self):
        """Get full IB symbol format"""
        return f"{self.symbol} {self.security_type} {self.exchange} {self.currency}"

class MarketData(models.Model):
    """Model to store real-time market data"""
    
    ticker = models.ForeignKey(MarketTicker, on_delete=models.CASCADE, related_name='market_data')
    
    # Price data
    bid_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    ask_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    last_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    close_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    open_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    high_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    low_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    
    # Volume data
    volume = models.BigIntegerField(null=True, blank=True)
    avg_volume = models.BigIntegerField(null=True, blank=True)
    
    # Market indicators
    bid_size = models.IntegerField(null=True, blank=True)
    ask_size = models.IntegerField(null=True, blank=True)
    last_size = models.IntegerField(null=True, blank=True)
    
    # Calculated fields
    price_change = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    price_change_percent = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    spread = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    market_timestamp = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ticker', '-timestamp']),
            models.Index(fields=['-timestamp']),
            models.Index(fields=['ticker', 'market_timestamp']),
        ]
    
    def __str__(self):
        return f"{self.ticker.symbol}: {self.last_price} @ {self.timestamp}"
    
    def calculate_spread(self):
        """Calculate bid-ask spread"""
        if self.bid_price and self.ask_price:
            return self.ask_price - self.bid_price
        return None
    
    def calculate_price_change(self):
        """Calculate price change from close"""
        if self.last_price and self.close_price:
            return self.last_price - self.close_price
        return None
    
    def calculate_price_change_percent(self):
        """Calculate price change percentage"""
        if self.last_price and self.close_price and self.close_price != 0:
            return ((self.last_price - self.close_price) / self.close_price) * 100
        return None

class HistoricalData(models.Model):
    """Model to store historical market data"""
    
    TIMEFRAME_CHOICES = [
        ('1min', '1 Minute'),
        ('5min', '5 Minutes'),
        ('15min', '15 Minutes'),
        ('30min', '30 Minutes'),
        ('1hour', '1 Hour'),
        ('1day', '1 Day'),
        ('1week', '1 Week'),
        ('1month', '1 Month'),
    ]
    
    ticker = models.ForeignKey(MarketTicker, on_delete=models.CASCADE, related_name='historical_data')
    timeframe = models.CharField(max_length=10, choices=TIMEFRAME_CHOICES, default='1day')
    
    # OHLCV data
    open_price = models.DecimalField(max_digits=12, decimal_places=4)
    high_price = models.DecimalField(max_digits=12, decimal_places=4)
    low_price = models.DecimalField(max_digits=12, decimal_places=4)
    close_price = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField()
    
    # Additional data
    adjusted_close = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    weighted_average_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    
    # Timestamps
    bar_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['ticker', 'timeframe', 'bar_time']
        ordering = ['-bar_time']
        indexes = [
            models.Index(fields=['ticker', 'timeframe', '-bar_time']),
            models.Index(fields=['ticker', 'bar_time']),
            models.Index(fields=['timeframe', '-bar_time']),
        ]
    
    def __str__(self):
        return f"{self.ticker.symbol} {self.timeframe}: {self.close_price} @ {self.bar_time}"
    
    def get_price_change(self):
        """Calculate price change for the bar"""
        return self.close_price - self.open_price
    
    def get_price_change_percent(self):
        """Calculate price change percentage for the bar"""
        if self.open_price != 0:
            return ((self.close_price - self.open_price) / self.open_price) * 100
        return None

class IBConnection(models.Model):
    """Model to store Interactive Brokers connection settings"""
    
    STATUS_CHOICES = [
        ('disconnected', 'Disconnected'),
        ('connecting', 'Connecting'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    host = models.CharField(max_length=100, default='127.0.0.1')
    port = models.IntegerField(default=7497)  # TWS: 7497, IB Gateway: 4001
    client_id = models.IntegerField(default=1)
    
    # Connection status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disconnected')
    last_connected = models.DateTimeField(null=True, blank=True)
    last_disconnected = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    auto_reconnect = models.BooleanField(default=True)
    timeout = models.IntegerField(default=30)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"
    
    def get_connection_string(self):
        """Get connection string for IB API"""
        return f"{self.host}:{self.port}:{self.client_id}"

class DataCollectionJob(models.Model):
    """Model to track data collection jobs"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    JOB_TYPE_CHOICES = [
        ('realtime', 'Real-time Data'),
        ('historical', 'Historical Data'),
        ('ticker_info', 'Ticker Information'),
        ('market_scan', 'Market Scan'),
    ]
    
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Job parameters
    tickers = models.JSONField(default=list, blank=True)  # List of ticker symbols
    timeframe = models.CharField(max_length=10, blank=True, null=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    
    # Progress tracking
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    successful_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)
    
    # Results
    results = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['job_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.job_type} Job - {self.status} ({self.created_at})"
    
    def get_progress_percentage(self):
        """Calculate job progress percentage"""
        if self.total_items > 0:
            return (self.processed_items / self.total_items) * 100
        return 0
    
    def is_completed(self):
        """Check if job is completed"""
        return self.status in ['completed', 'failed', 'cancelled']

# Trading Signal Models

class TradingSignal(models.Model):
    """Model to store generated trading signals combining GPT analysis and market data"""
    
    SIGNAL_TYPE_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
        ('strong_buy', 'Strong Buy'),
        ('strong_sell', 'Strong Sell'),
    ]
    
    SIGNAL_SOURCE_CHOICES = [
        ('gpt_analysis', 'GPT Analysis'),
        ('market_data', 'Market Data'),
        ('combined', 'Combined Analysis'),
        ('technical', 'Technical Analysis'),
        ('sentiment', 'Sentiment Analysis'),
    ]
    
    SIGNAL_STATUS_CHOICES = [
        ('active', 'Active'),
        ('executed', 'Executed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core signal information
    ticker = models.ForeignKey(MarketTicker, on_delete=models.CASCADE, related_name='signals')
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPE_CHOICES)
    confidence = models.FloatField(help_text="Confidence score from 0.0 to 1.0")
    source = models.CharField(max_length=20, choices=SIGNAL_SOURCE_CHOICES, default='combined')
    status = models.CharField(max_length=20, choices=SIGNAL_STATUS_CHOICES, default='active')
    
    # Signal metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    expiry_time = models.DateTimeField(null=True, blank=True)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Analysis components
    sentiment_score = models.FloatField(null=True, blank=True)
    sentiment_label = models.CharField(max_length=20, null=True, blank=True)
    market_data_score = models.FloatField(null=True, blank=True)
    technical_score = models.FloatField(null=True, blank=True)
    combined_score = models.FloatField(null=True, blank=True)
    
    # Reasoning and context
    reasoning = models.TextField(help_text="Detailed reasoning for the signal")
    market_context = models.JSONField(default=dict, blank=True)
    risk_assessment = models.TextField(blank=True, null=True)
    
    # Related data
    related_articles = models.ManyToManyField(NewsArticle, blank=True, related_name='signals')
    related_market_data = models.ForeignKey(MarketData, on_delete=models.SET_NULL, null=True, blank=True, related_name='signals')
    
    # Performance tracking
    execution_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    execution_time = models.DateTimeField(null=True, blank=True)
    performance_score = models.FloatField(null=True, blank=True)
    
    # User tracking
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ticker', 'signal_type']),
            models.Index(fields=['confidence', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
            models.Index(fields=['source', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.ticker.symbol}: {self.get_signal_type_display()} ({self.confidence:.2f}) - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def get_confidence_display(self):
        """Get confidence as percentage"""
        return f"{self.confidence * 100:.1f}%"
    
    def get_risk_level(self):
        """Get risk level based on confidence and signal type"""
        if self.confidence >= 0.8:
            risk = "Low"
        elif self.confidence >= 0.6:
            risk = "Medium"
        else:
            risk = "High"
        
        if self.signal_type in ['hold']:
            risk = "Minimal"
        
        return risk
    
    def get_signal_strength(self):
        """Get signal strength based on confidence and type"""
        if self.signal_type in ['strong_buy', 'strong_sell']:
            return "Strong"
        elif self.confidence >= 0.7:
            return "Moderate"
        else:
            return "Weak"
    
    def is_expired(self):
        """Check if signal has expired"""
        if self.expiry_time:
            return timezone.now() > self.expiry_time
        return False
    
    def get_time_to_expiry(self):
        """Get time remaining until expiry"""
        if self.expiry_time:
            delta = self.expiry_time - timezone.now()
            if delta.total_seconds() > 0:
                return delta
        return None
    
    def calculate_performance(self):
        """Calculate performance score if executed"""
        if self.execution_price and self.target_price:
            if self.signal_type in ['buy', 'strong_buy']:
                performance = (self.target_price - self.execution_price) / self.execution_price
            else:  # sell signals
                performance = (self.execution_price - self.target_price) / self.execution_price
            
            self.performance_score = performance
            self.save()
            return performance
        return None

class SignalMetadata(models.Model):
    """Model to store additional metadata for trading signals"""
    
    signal = models.OneToOneField(TradingSignal, on_delete=models.CASCADE, related_name='metadata')
    
    # Market conditions at signal generation
    market_volatility = models.FloatField(null=True, blank=True)
    market_trend = models.CharField(max_length=20, null=True, blank=True)
    sector_performance = models.JSONField(default=dict, blank=True)
    
    # Technical indicators
    rsi = models.FloatField(null=True, blank=True)
    macd = models.FloatField(null=True, blank=True)
    moving_average_20 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    moving_average_50 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bollinger_upper = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bollinger_lower = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Volume analysis
    volume_ratio = models.FloatField(null=True, blank=True)
    average_volume = models.BigIntegerField(null=True, blank=True)
    
    # News impact
    news_sentiment_score = models.FloatField(null=True, blank=True)
    news_impact_score = models.FloatField(null=True, blank=True)
    recent_news_count = models.IntegerField(default=0)
    
    # Additional context
    market_cap_category = models.CharField(max_length=20, null=True, blank=True)
    sector_rank = models.IntegerField(null=True, blank=True)
    peer_performance = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Metadata for {self.signal}"
    
    def get_technical_summary(self):
        """Get summary of technical indicators"""
        indicators = []
        if self.rsi:
            indicators.append(f"RSI: {self.rsi:.2f}")
        if self.macd:
            indicators.append(f"MACD: {self.macd:.4f}")
        if self.moving_average_20:
            indicators.append(f"MA20: ${self.moving_average_20}")
        if self.moving_average_50:
            indicators.append(f"MA50: ${self.moving_average_50}")
        
        return ", ".join(indicators) if indicators else "No technical data"


# API Access Models for External Systems
class APISubscriber(models.Model):
    """Model for external systems that subscribe to trading signals"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending Approval'),
    ]
    
    name = models.CharField(max_length=200, help_text="Name of the external system/company")
    description = models.TextField(blank=True, help_text="Description of the subscriber")
    contact_email = models.EmailField(help_text="Contact email for the subscriber")
    webhook_url = models.URLField(blank=True, help_text="Webhook URL for real-time signal delivery")
    api_key = models.CharField(max_length=64, unique=True, help_text="API key for authentication")
    secret_key = models.CharField(max_length=64, help_text="Secret key for webhook authentication")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    request_count = models.PositiveIntegerField(default=0)
    rate_limit_per_hour = models.PositiveIntegerField(default=1000, help_text="Maximum requests per hour")
    
    # Subscription preferences
    subscribed_tickers = models.JSONField(default=list, help_text="List of ticker symbols to receive signals for")
    min_confidence_threshold = models.DecimalField(max_digits=3, decimal_places=2, default=0.50, 
                                                 help_text="Minimum confidence threshold for signals")
    signal_types = models.JSONField(default=list, help_text="Types of signals to receive (buy, sell, hold)")
    
    class Meta:
        db_table = 'api_subscribers'
        verbose_name = 'API Subscriber'
        verbose_name_plural = 'API Subscribers'
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = self.generate_api_key()
        if not self.secret_key:
            self.secret_key = self.generate_secret_key()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_api_key():
        """Generate a secure API key"""
        alphabet = string.ascii_letters + string.digits
        return 'tp_' + ''.join(secrets.choice(alphabet) for _ in range(32))
    
    @staticmethod
    def generate_secret_key():
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)
    
    def is_rate_limited(self):
        """Check if subscriber has exceeded rate limit"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Reset counter if it's been more than an hour
        if self.last_accessed and timezone.now() - self.last_accessed > timedelta(hours=1):
            self.request_count = 0
            self.save()
        
        return self.request_count >= self.rate_limit_per_hour
    
    def increment_request_count(self):
        """Increment the request count and update last accessed time"""
        from django.utils import timezone
        self.request_count += 1
        self.last_accessed = timezone.now()
        self.save()


class APIAccessLog(models.Model):
    """Log API access for monitoring and debugging"""
    
    REQUEST_TYPE_CHOICES = [
        ('signal', 'Signal Request'),
        ('webhook', 'Webhook Delivery'),
        ('auth', 'Authentication'),
        ('rate_limit', 'Rate Limit Exceeded'),
    ]
    
    subscriber = models.ForeignKey(APISubscriber, on_delete=models.CASCADE, related_name='access_logs')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    request_data = models.JSONField(default=dict, blank=True)
    response_status = models.PositiveIntegerField()
    response_data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_access_logs'
        verbose_name = 'API Access Log'
        verbose_name_plural = 'API Access Logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.subscriber.name} - {self.request_type} - {self.timestamp}"


class SignalDelivery(models.Model):
    """Track signal deliveries to external subscribers"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    signal = models.ForeignKey('TradingSignal', on_delete=models.CASCADE, related_name='deliveries')
    subscriber = models.ForeignKey(APISubscriber, on_delete=models.CASCADE, related_name='signal_deliveries')
    delivery_method = models.CharField(max_length=20, choices=[('webhook', 'Webhook'), ('polling', 'Polling')])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_attempts = models.PositiveIntegerField(default=0)
    last_attempt = models.DateTimeField(null=True, blank=True)
    next_retry = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'signal_deliveries'
        verbose_name = 'Signal Delivery'
        verbose_name_plural = 'Signal Deliveries'
        unique_together = ['signal', 'subscriber']
    
    def __str__(self):
        return f"{self.signal.ticker} signal to {self.subscriber.name} - {self.status}"
