import openai
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.core.cache import cache
from .models import NewsArticle, TradingRecommendation

logger = logging.getLogger(__name__)

class GPTNewsAnalyzer:
    """GPT-powered news analysis service with token optimization"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("OpenAI API key not configured. GPT analysis will be disabled.")
        
        # Token optimization settings
        self.max_tokens_per_request = 1000  # Conservative limit
        self.cache_duration = 3600  # 1 hour cache
        
        # Optimized prompts for minimal token usage
        self.sentiment_prompt = """Analyze sentiment: {title} {summary}
Output: {{"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0, "reason": "brief reason"}}"""

        self.classification_prompt = """Classify news impact: {title} {summary}
Output: {{"impact": "high/medium/low", "sectors": ["sector1", "sector2"], "confidence": 0.0-1.0}}"""

        self.trading_prompt = """Generate trading recommendation for {ticker} based on: {title} {summary}
Output: {{"action": "buy/sell/hold", "confidence": 0.0-1.0, "reason": "brief reason", "timeframe": "short/medium/long"}}"""

    def analyze_article_sentiment(self, article: NewsArticle) -> Dict[str, Any]:
        """Analyze article sentiment with caching and token optimization"""
        cache_key = f"sentiment_{article.id}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info(f"Using cached sentiment for article {article.id}")
            return cached_result
        
        if not self.api_key:
            return self._get_default_sentiment()
        
        try:
            # Optimize input to minimize tokens
            title = article.title[:100] if article.title else ""
            summary = article.summary[:200] if article.summary else ""
            
            prompt = self.sentiment_prompt.format(title=title, summary=summary)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial news analyst. Provide concise, structured responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens_per_request,
                temperature=0.3
            )
            
            result = self._parse_gpt_response(response.choices[0].message.content)
            result['article_id'] = article.id
            result['model'] = 'gpt-3.5-turbo'
            
            # Cache the result
            cache.set(cache_key, result, self.cache_duration)
            
            logger.info(f"GPT sentiment analysis completed for article {article.id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in GPT sentiment analysis: {e}")
            return self._get_default_sentiment()
    
    def classify_news_impact(self, article: NewsArticle) -> Dict[str, Any]:
        """Classify news impact and relevance with caching"""
        cache_key = f"impact_{article.id}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        if not self.api_key:
            return self._get_default_impact()
        
        try:
            title = article.title[:100] if article.title else ""
            summary = article.summary[:200] if article.summary else ""
            
            prompt = self.classification_prompt.format(title=title, summary=summary)
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial analyst. Classify news impact concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens_per_request,
                temperature=0.3
            )
            
            result = self._parse_gpt_response(response.choices[0].message.content)
            result['article_id'] = article.id
            result['model'] = 'gpt-3.5-turbo'
            
            cache.set(cache_key, result, self.cache_duration)
            return result
            
        except Exception as e:
            logger.error(f"Error in GPT impact classification: {e}")
            return self._get_default_impact()
    
    def generate_trading_recommendation(self, ticker: str, articles: List[NewsArticle]) -> Dict[str, Any]:
        """Generate trading recommendation based on multiple articles"""
        if not articles:
            return self._get_default_recommendation(ticker)
        
        if not self.api_key:
            return self._get_default_recommendation(ticker)
        
        try:
            # Aggregate article information to minimize tokens
            combined_text = self._combine_articles_for_analysis(articles)
            
            prompt = self.trading_prompt.format(
                ticker=ticker,
                title=combined_text[:150],
                summary=combined_text[150:350] if len(combined_text) > 150 else ""
            )
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a trading analyst. Provide actionable recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens_per_request,
                temperature=0.3
            )
            
            result = self._parse_gpt_response(response.choices[0].message.content)
            result['ticker'] = ticker
            result['articles_analyzed'] = len(articles)
            result['model'] = 'gpt-3.5-turbo'
            
            return result
            
        except Exception as e:
            logger.error(f"Error in GPT trading recommendation: {e}")
            return self._get_default_recommendation(ticker)
    
    def batch_analyze_articles(self, articles: List[NewsArticle]) -> List[Dict[str, Any]]:
        """Batch analyze multiple articles for efficiency"""
        results = []
        
        for article in articles:
            try:
                # Get sentiment and impact analysis
                sentiment = self.analyze_article_sentiment(article)
                impact = self.classify_news_impact(article)
                
                # Combine results
                analysis_result = {
                    'article_id': article.id,
                    'title': article.title,
                    'source': article.source,
                    'sentiment': sentiment,
                    'impact': impact,
                    'combined_score': self._calculate_combined_score(sentiment, impact)
                }
                
                results.append(analysis_result)
                
            except Exception as e:
                logger.error(f"Error analyzing article {article.id}: {e}")
                continue
        
        return results
    
    def _combine_articles_for_analysis(self, articles: List[NewsArticle]) -> str:
        """Combine multiple articles into a single analysis text"""
        if not articles:
            return ""
        
        # Take key information from each article
        combined_parts = []
        for article in articles[:3]:  # Limit to 3 articles to save tokens
            title = article.title[:50] if article.title else ""
            summary = article.summary[:100] if article.summary else ""
            if title or summary:
                combined_parts.append(f"{title}: {summary}")
        
        return " | ".join(combined_parts)
    
    def _calculate_combined_score(self, sentiment: Dict, impact: Dict) -> float:
        """Calculate a combined score from sentiment and impact analysis"""
        try:
            sentiment_score = float(sentiment.get('confidence', 0.5))
            impact_score = float(impact.get('confidence', 0.5))
            
            # Weight sentiment more heavily
            combined = (sentiment_score * 0.7) + (impact_score * 0.3)
            return round(combined, 3)
            
        except (ValueError, TypeError):
            return 0.5
    
    def _parse_gpt_response(self, response_text: str) -> Dict[str, Any]:
        """Parse GPT response and handle errors gracefully"""
        try:
            # Try to extract JSON from response
            if '{' in response_text and '}' in response_text:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                # Fallback parsing
                return self._fallback_parsing(response_text)
                
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse GPT response as JSON: {response_text}")
            return self._fallback_parsing(response_text)
    
    def _fallback_parsing(self, response_text: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails"""
        response_lower = response_text.lower()
        
        # Sentiment parsing
        if 'positive' in response_lower:
            sentiment = 'positive'
        elif 'negative' in response_lower:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Confidence parsing
        confidence = 0.5  # Default
        if 'confidence' in response_lower:
            try:
                # Look for numbers in the text
                import re
                numbers = re.findall(r'\d+\.?\d*', response_text)
                if numbers:
                    confidence = min(float(numbers[0]), 1.0)
            except:
                pass
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'reason': 'Parsed from GPT response',
            'parsing_method': 'fallback'
        }
    
    def _get_default_sentiment(self) -> Dict[str, Any]:
        """Return default sentiment when GPT is unavailable"""
        return {
            'sentiment': 'neutral',
            'confidence': 0.5,
            'reason': 'GPT analysis unavailable',
            'model': 'default'
        }
    
    def _get_default_impact(self) -> Dict[str, Any]:
        """Return default impact classification when GPT is unavailable"""
        return {
            'impact': 'medium',
            'sectors': ['general'],
            'confidence': 0.5,
            'model': 'default'
        }
    
    def _get_default_recommendation(self, ticker: str) -> Dict[str, Any]:
        """Return default trading recommendation when GPT is unavailable"""
        return {
            'ticker': ticker,
            'action': 'hold',
            'confidence': 0.5,
            'reason': 'GPT analysis unavailable',
            'timeframe': 'medium',
            'model': 'default'
        }
    
    def get_token_usage_stats(self) -> Dict[str, Any]:
        """Get token usage statistics for monitoring"""
        return {
            'max_tokens_per_request': self.max_tokens_per_request,
            'cache_duration': self.cache_duration,
            'cache_enabled': True,
            'optimization_enabled': True
        }



