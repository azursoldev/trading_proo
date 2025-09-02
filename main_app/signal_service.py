"""
Trading Signal Generation Service

This service combines GPT-based analysis with real-time market data
to generate structured trading signals with metadata.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.db.models import Q, Avg, Count
import numpy as np

from .models import (
    TradingSignal, SignalMetadata, MarketTicker, MarketData, 
    NewsArticle, NewsAnalysis, TradingRecommendation, HistoricalData
)
from .gpt_service import GPTNewsAnalyzer

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Main class for generating trading signals"""
    
    def __init__(self):
        self.gpt_analyzer = GPTNewsAnalyzer()
    
    def generate_signal(self, ticker_symbol: str, source: str = 'combined') -> Optional[TradingSignal]:
        """
        Generate a trading signal for a given ticker
        
        Args:
            ticker_symbol: Stock ticker symbol (e.g., 'AAPL')
            source: Signal source ('gpt_analysis', 'market_data', 'combined')
        
        Returns:
            TradingSignal object or None if generation fails
        """
        try:
            # Get ticker object
            ticker = MarketTicker.objects.filter(symbol=ticker_symbol).first()
            if not ticker:
                logger.error(f"Ticker {ticker_symbol} not found")
                return None
            
            # Get latest market data
            latest_market_data = MarketData.objects.filter(ticker=ticker).order_by('-timestamp').first()
            
            # Get recent news articles
            recent_articles = self._get_recent_articles(ticker_symbol)
            
            # Generate signal based on source
            if source == 'gpt_analysis':
                signal = self._generate_gpt_signal(ticker, recent_articles)
            elif source == 'market_data':
                signal = self._generate_market_data_signal(ticker, latest_market_data)
            elif source == 'combined':
                signal = self._generate_combined_signal(ticker, latest_market_data, recent_articles)
            else:
                logger.error(f"Unknown signal source: {source}")
                return None
            
            if signal:
                # Create metadata
                self._create_signal_metadata(signal, latest_market_data, recent_articles)
                logger.info(f"Generated signal for {ticker_symbol}: {signal.signal_type} ({signal.confidence:.2f})")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {ticker_symbol}: {str(e)}")
            return None
    
    def _get_recent_articles(self, ticker_symbol: str, days: int = 7) -> List[NewsArticle]:
        """Get recent news articles related to the ticker"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Search for articles containing the ticker symbol
        articles = NewsArticle.objects.filter(
            Q(title__icontains=ticker_symbol) |
            Q(content__icontains=ticker_symbol) |
            Q(summary__icontains=ticker_symbol),
            scraped_date__gte=cutoff_date
        ).order_by('-scraped_date')[:10]
        
        return list(articles)
    
    def _generate_gpt_signal(self, ticker: MarketTicker, articles: List[NewsArticle]) -> Optional[TradingSignal]:
        """Generate signal based on GPT analysis of news articles"""
        if not articles:
            return None
        
        try:
            # Analyze articles with GPT
            analysis_results = []
            total_sentiment = 0
            total_impact = 0
            analyzed_count = 0
            
            for article in articles:
                if not article.gpt_sentiment:
                    # Analyze with GPT if not already analyzed
                    analysis = self.gpt_analyzer.analyze_article(article.id)
                    if analysis:
                        article.refresh_from_db()
                
                if article.gpt_sentiment and article.gpt_impact:
                    # Convert sentiment to numeric score
                    sentiment_score = self._sentiment_to_score(article.gpt_sentiment)
                    impact_score = self._impact_to_score(article.gpt_impact)
                    
                    total_sentiment += sentiment_score * (article.gpt_sentiment_confidence or 0.5)
                    total_impact += impact_score * (article.gpt_impact_confidence or 0.5)
                    analyzed_count += 1
            
            if analyzed_count == 0:
                return None
            
            # Calculate average scores
            avg_sentiment = total_sentiment / analyzed_count
            avg_impact = total_impact / analyzed_count
            
            # Determine signal type and confidence
            signal_type, confidence = self._calculate_signal_from_scores(avg_sentiment, avg_impact)
            
            # Create signal
            signal = TradingSignal.objects.create(
                ticker=ticker,
                signal_type=signal_type,
                confidence=confidence,
                source='gpt_analysis',
                sentiment_score=avg_sentiment,
                sentiment_label=self._score_to_sentiment(avg_sentiment),
                reasoning=f"Based on analysis of {analyzed_count} recent news articles. "
                         f"Average sentiment: {avg_sentiment:.2f}, Impact: {avg_impact:.2f}",
                market_context={
                    'articles_analyzed': analyzed_count,
                    'sentiment_breakdown': self._get_sentiment_breakdown(articles),
                    'impact_breakdown': self._get_impact_breakdown(articles)
                }
            )
            
            # Link related articles
            signal.related_articles.set(articles)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in GPT signal generation: {str(e)}")
            return None
    
    def _generate_market_data_signal(self, ticker: MarketTicker, market_data: Optional[MarketData]) -> Optional[TradingSignal]:
        """Generate signal based on market data analysis"""
        if not market_data:
            return None
        
        try:
            # Get historical data for technical analysis
            historical_data = self._get_historical_data(ticker, days=30)
            
            # Calculate technical indicators
            technical_scores = self._calculate_technical_indicators(historical_data, market_data)
            
            # Determine signal based on technical analysis
            signal_type, confidence = self._calculate_technical_signal(technical_scores, market_data)
            
            # Create signal
            signal = TradingSignal.objects.create(
                ticker=ticker,
                signal_type=signal_type,
                confidence=confidence,
                source='market_data',
                market_data_score=technical_scores.get('overall_score', 0.5),
                technical_score=technical_scores.get('overall_score', 0.5),
                reasoning=f"Based on technical analysis. Price: ${market_data.last_price}, "
                         f"Volume: {market_data.volume}, Technical Score: {technical_scores.get('overall_score', 0.5):.2f}",
                market_context={
                    'current_price': float(market_data.last_price) if market_data.last_price else 0.0,
                    'volume': market_data.volume,
                    'technical_indicators': technical_scores
                },
                related_market_data=market_data
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error in market data signal generation: {str(e)}")
            return None
    
    def _generate_combined_signal(self, ticker: MarketTicker, market_data: Optional[MarketData], articles: List[NewsArticle]) -> Optional[TradingSignal]:
        """Generate signal combining GPT analysis and market data"""
        try:
            # Get GPT signal
            gpt_signal = self._generate_gpt_signal(ticker, articles)
            
            # Get market data signal
            market_signal = self._generate_market_data_signal(ticker, market_data)
            
            if not gpt_signal and not market_signal:
                return None
            
            # Combine signals
            if gpt_signal and market_signal:
                # Weighted combination (60% GPT, 40% technical)
                combined_confidence = (gpt_signal.confidence * 0.6) + (market_signal.confidence * 0.4)
                
                # Determine combined signal type
                combined_type = self._combine_signal_types(gpt_signal.signal_type, market_signal.signal_type)
                
                # Create combined signal
                signal = TradingSignal.objects.create(
                    ticker=ticker,
                    signal_type=combined_type,
                    confidence=combined_confidence,
                    source='combined',
                    sentiment_score=gpt_signal.sentiment_score,
                    sentiment_label=gpt_signal.sentiment_label,
                    market_data_score=market_signal.market_data_score,
                    technical_score=market_signal.technical_score,
                    combined_score=combined_confidence,
                    reasoning=f"Combined analysis: GPT ({gpt_signal.confidence:.2f}) + Technical ({market_signal.confidence:.2f}). "
                             f"GPT: {gpt_signal.signal_type}, Technical: {market_signal.signal_type}",
                    market_context={
                        'gpt_analysis': {
                            'signal_type': gpt_signal.signal_type,
                            'confidence': gpt_signal.confidence,
                            'sentiment': gpt_signal.sentiment_score
                        },
                        'technical_analysis': {
                            'signal_type': market_signal.signal_type,
                            'confidence': market_signal.confidence,
                            'technical_score': market_signal.technical_score
                        }
                    },
                    related_market_data=market_data
                )
                
                # Link related articles
                signal.related_articles.set(articles)
                
                # Clean up individual signals
                gpt_signal.delete()
                market_signal.delete()
                
                return signal
            
            # Return the available signal
            return gpt_signal or market_signal
            
        except Exception as e:
            logger.error(f"Error in combined signal generation: {str(e)}")
            return None
    
    def _create_signal_metadata(self, signal: TradingSignal, market_data: Optional[MarketData], articles: List[NewsArticle]):
        """Create metadata for the signal"""
        try:
            metadata = SignalMetadata.objects.create(
                signal=signal,
                recent_news_count=len(articles),
                news_sentiment_score=signal.sentiment_score,
                news_impact_score=self._calculate_news_impact(articles)
            )
            
            if market_data:
                metadata.volume_ratio = self._calculate_volume_ratio(ticker=signal.ticker, current_volume=market_data.volume)
                metadata.average_volume = self._get_average_volume(signal.ticker)
            
            # Add technical indicators if available
            if signal.technical_score:
                historical_data = self._get_historical_data(signal.ticker, days=50)
                if historical_data:
                    technical_indicators = self._calculate_technical_indicators(historical_data, market_data)
                    metadata.rsi = technical_indicators.get('rsi')
                    metadata.macd = technical_indicators.get('macd')
                    metadata.moving_average_20 = technical_indicators.get('ma_20')
                    metadata.moving_average_50 = technical_indicators.get('ma_50')
                    metadata.bollinger_upper = technical_indicators.get('bb_upper')
                    metadata.bollinger_lower = technical_indicators.get('bb_lower')
            
            metadata.save()
            
        except Exception as e:
            logger.error(f"Error creating signal metadata: {str(e)}")
    
    def _sentiment_to_score(self, sentiment: str) -> float:
        """Convert sentiment string to numeric score"""
        sentiment_map = {
            'positive': 0.7,
            'negative': -0.7,
            'neutral': 0.0
        }
        return sentiment_map.get(sentiment, 0.0)
    
    def _impact_to_score(self, impact: str) -> float:
        """Convert impact string to numeric score"""
        impact_map = {
            'high': 1.0,
            'medium': 0.5,
            'low': 0.2
        }
        return impact_map.get(impact, 0.0)
    
    def _score_to_sentiment(self, score: float) -> str:
        """Convert numeric score to sentiment string"""
        if score > 0.3:
            return 'positive'
        elif score < -0.3:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_signal_from_scores(self, sentiment_score: float, impact_score: float) -> Tuple[str, float]:
        """Calculate signal type and confidence from sentiment and impact scores"""
        # Combine sentiment and impact
        combined_score = (sentiment_score * 0.7) + (impact_score * 0.3)
        
        # Determine signal type
        if combined_score > 0.5:
            signal_type = 'strong_buy' if combined_score > 0.8 else 'buy'
        elif combined_score < -0.5:
            signal_type = 'strong_sell' if combined_score < -0.8 else 'sell'
        else:
            signal_type = 'hold'
        
        # Calculate confidence based on score magnitude and impact
        confidence = min(abs(combined_score) * impact_score, 1.0)
        confidence = max(confidence, 0.1)  # Minimum confidence
        
        return signal_type, confidence
    
    def _get_sentiment_breakdown(self, articles: List[NewsArticle]) -> Dict[str, int]:
        """Get breakdown of sentiment in articles"""
        breakdown = {'positive': 0, 'negative': 0, 'neutral': 0}
        for article in articles:
            if article.gpt_sentiment:
                breakdown[article.gpt_sentiment] += 1
        return breakdown
    
    def _get_impact_breakdown(self, articles: List[NewsArticle]) -> Dict[str, int]:
        """Get breakdown of impact in articles"""
        breakdown = {'high': 0, 'medium': 0, 'low': 0}
        for article in articles:
            if article.gpt_impact:
                breakdown[article.gpt_impact] += 1
        return breakdown
    
    def _get_historical_data(self, ticker: MarketTicker, days: int = 30) -> List[Dict]:
        """Get historical data for technical analysis"""
        cutoff_date = timezone.now() - timedelta(days=days)
        historical = HistoricalData.objects.filter(
            ticker=ticker,
            bar_time__gte=cutoff_date
        ).order_by('bar_time')
        
        return [
            {
                'date': h.bar_time,
                'open': float(h.open_price),
                'high': float(h.high_price),
                'low': float(h.low_price),
                'close': float(h.close_price),
                'volume': h.volume
            }
            for h in historical
        ]
    
    def _calculate_technical_indicators(self, historical_data: List[Dict], market_data: Optional[MarketData]) -> Dict:
        """Calculate technical indicators"""
        if not historical_data:
            return {'overall_score': 0.5}
        
        try:
            closes = [d['close'] for d in historical_data]
            volumes = [d['volume'] for d in historical_data]
            
            # Simple moving averages
            ma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
            ma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else np.mean(closes)
            
            # RSI calculation
            rsi = self._calculate_rsi(closes)
            
            # MACD calculation
            macd = self._calculate_macd(closes)
            
            # Bollinger Bands
            bb_upper, bb_lower = self._calculate_bollinger_bands(closes)
            
            # Overall technical score
            current_price = float(market_data.last_price) if market_data else closes[-1]
            
            # Price vs moving averages
            price_vs_ma20 = (current_price - ma_20) / ma_20
            price_vs_ma50 = (current_price - ma_50) / ma_50
            
            # Volume analysis
            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
            volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0
            
            # Calculate overall score
            overall_score = 0.5  # Neutral starting point
            
            # Price momentum
            if price_vs_ma20 > 0.02:  # 2% above MA20
                overall_score += 0.2
            elif price_vs_ma20 < -0.02:  # 2% below MA20
                overall_score -= 0.2
            
            if price_vs_ma50 > 0.05:  # 5% above MA50
                overall_score += 0.1
            elif price_vs_ma50 < -0.05:  # 5% below MA50
                overall_score -= 0.1
            
            # RSI signals
            if rsi < 30:  # Oversold
                overall_score += 0.15
            elif rsi > 70:  # Overbought
                overall_score -= 0.15
            
            # Volume confirmation
            if volume_ratio > 1.5:  # High volume
                overall_score += 0.1
            elif volume_ratio < 0.5:  # Low volume
                overall_score -= 0.05
            
            # Normalize score
            overall_score = max(0.0, min(1.0, overall_score))
            
            return {
                'overall_score': overall_score,
                'rsi': rsi,
                'macd': macd,
                'ma_20': Decimal(str(ma_20)),
                'ma_50': Decimal(str(ma_50)),
                'bb_upper': Decimal(str(bb_upper)),
                'bb_lower': Decimal(str(bb_lower)),
                'price_vs_ma20': price_vs_ma20,
                'price_vs_ma50': price_vs_ma50,
                'volume_ratio': volume_ratio
            }
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return {'overall_score': 0.5}
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: List[float]) -> float:
        """Calculate MACD indicator"""
        if len(prices) < 26:
            return 0.0
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        return ema_12 - ema_26
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return prices[-1], prices[-1]
        
        recent_prices = prices[-period:]
        sma = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, lower_band
    
    def _calculate_technical_signal(self, technical_scores: Dict, market_data: Optional[MarketData]) -> Tuple[str, float]:
        """Calculate signal type and confidence from technical analysis"""
        overall_score = technical_scores.get('overall_score', 0.5)
        
        # Determine signal type
        if overall_score > 0.7:
            signal_type = 'strong_buy'
        elif overall_score > 0.6:
            signal_type = 'buy'
        elif overall_score < 0.3:
            signal_type = 'strong_sell'
        elif overall_score < 0.4:
            signal_type = 'sell'
        else:
            signal_type = 'hold'
        
        # Calculate confidence
        confidence = abs(overall_score - 0.5) * 2  # Convert to 0-1 scale
        confidence = max(confidence, 0.1)  # Minimum confidence
        
        return signal_type, confidence
    
    def _combine_signal_types(self, gpt_type: str, technical_type: str) -> str:
        """Combine GPT and technical signal types"""
        # Simple combination logic
        if gpt_type == technical_type:
            return gpt_type
        
        # If one is strong and other is weak, use the strong one
        if 'strong' in gpt_type and 'strong' not in technical_type:
            return gpt_type
        if 'strong' in technical_type and 'strong' not in gpt_type:
            return technical_type
        
        # If both are buy/sell, use the stronger one
        if gpt_type in ['buy', 'strong_buy'] and technical_type in ['buy', 'strong_buy']:
            return 'strong_buy' if 'strong' in gpt_type or 'strong' in technical_type else 'buy'
        
        if gpt_type in ['sell', 'strong_sell'] and technical_type in ['sell', 'strong_sell']:
            return 'strong_sell' if 'strong' in gpt_type or 'strong' in technical_type else 'sell'
        
        # If conflicting, default to hold
        return 'hold'
    
    def _calculate_news_impact(self, articles: List[NewsArticle]) -> float:
        """Calculate overall news impact score"""
        if not articles:
            return 0.0
        
        total_impact = 0
        count = 0
        
        for article in articles:
            if article.gpt_impact:
                impact_score = self._impact_to_score(article.gpt_impact)
                confidence = article.gpt_impact_confidence or 0.5
                total_impact += impact_score * confidence
                count += 1
        
        return total_impact / count if count > 0 else 0.0
    
    def _calculate_volume_ratio(self, ticker: MarketTicker, current_volume: int) -> float:
        """Calculate volume ratio compared to average"""
        try:
            # Get average volume from last 20 days
            cutoff_date = timezone.now() - timedelta(days=20)
            avg_volume = MarketData.objects.filter(
                ticker=ticker,
                timestamp__gte=cutoff_date
            ).aggregate(avg_vol=Avg('volume'))['avg_vol']
            
            if avg_volume and avg_volume > 0:
                return current_volume / avg_volume
            return 1.0
            
        except Exception:
            return 1.0
    
    def _get_average_volume(self, ticker: MarketTicker) -> Optional[int]:
        """Get average volume for ticker"""
        try:
            cutoff_date = timezone.now() - timedelta(days=30)
            avg_volume = MarketData.objects.filter(
                ticker=ticker,
                timestamp__gte=cutoff_date
            ).aggregate(avg_vol=Avg('volume'))['avg_vol']
            
            return int(avg_volume) if avg_volume else None
            
        except Exception:
            return None

class SignalManager:
    """Manager class for signal operations"""
    
    @staticmethod
    def get_active_signals(ticker_symbol: Optional[str] = None) -> List[TradingSignal]:
        """Get active signals, optionally filtered by ticker"""
        queryset = TradingSignal.objects.filter(status='active')
        
        if ticker_symbol:
            queryset = queryset.filter(ticker__symbol=ticker_symbol)
        
        return list(queryset.order_by('-timestamp'))
    
    @staticmethod
    def get_signals_by_confidence(min_confidence: float = 0.0) -> List[TradingSignal]:
        """Get signals above minimum confidence threshold"""
        return list(TradingSignal.objects.filter(
            confidence__gte=min_confidence,
            status='active'
        ).order_by('-confidence', '-timestamp'))
    
    @staticmethod
    def get_signals_by_type(signal_type: str) -> List[TradingSignal]:
        """Get signals of specific type"""
        return list(TradingSignal.objects.filter(
            signal_type=signal_type,
            status='active'
        ).order_by('-timestamp'))
    
    @staticmethod
    def expire_old_signals():
        """Mark old signals as expired"""
        expired_count = TradingSignal.objects.filter(
            status='active',
            expiry_time__lt=timezone.now()
        ).update(status='expired')
        
        logger.info(f"Expired {expired_count} old signals")
        return expired_count
    
    @staticmethod
    def get_signal_performance_stats() -> Dict:
        """Get signal performance statistics"""
        executed_signals = TradingSignal.objects.filter(
            status='executed',
            performance_score__isnull=False
        )
        
        if not executed_signals.exists():
            return {
                'total_signals': 0,
                'average_performance': 0.0,
                'success_rate': 0.0,
                'best_performance': 0.0,
                'worst_performance': 0.0
            }
        
        performances = [s.performance_score for s in executed_signals]
        positive_performances = [p for p in performances if p > 0]
        
        return {
            'total_signals': len(performances),
            'average_performance': np.mean(performances),
            'success_rate': len(positive_performances) / len(performances),
            'best_performance': max(performances),
            'worst_performance': min(performances)
        }
