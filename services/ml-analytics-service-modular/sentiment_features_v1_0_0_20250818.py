"""
Sentiment Feature Engine v1.0.0
News-basierte Sentiment-Features für ML Analytics Service

Autor: Claude Code
Datum: 18. August 2025
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncpg

# Mock News Data für Demonstration
MOCK_NEWS_DATA = {
    "AAPL": [
        {
            "title": "Apple Reports Strong Q3 Earnings, iPhone Sales Beat Expectations",
            "content": "Apple Inc. delivered impressive third-quarter results with iPhone sales exceeding analyst forecasts...",
            "sentiment_score": 0.8,
            "published_at": "2025-08-17T10:30:00Z",
            "source": "Reuters"
        },
        {
            "title": "Apple Faces Regulatory Challenges in European Markets",
            "content": "European regulators are increasing scrutiny on Apple's App Store policies...",
            "sentiment_score": -0.3,
            "published_at": "2025-08-16T14:20:00Z",
            "source": "Bloomberg"
        },
        {
            "title": "Apple Unveils New AI Features for iOS, Stock Rises",
            "content": "Apple's latest AI integration announcements have boosted investor confidence...",
            "sentiment_score": 0.6,
            "published_at": "2025-08-15T09:15:00Z",
            "source": "TechCrunch"
        },
        {
            "title": "Apple Supply Chain Concerns Impact Production Outlook",
            "content": "Ongoing supply chain disruptions may affect Apple's production capacity...",
            "sentiment_score": -0.4,
            "published_at": "2025-08-14T16:45:00Z",
            "source": "CNBC"
        },
        {
            "title": "Apple Services Revenue Continues Strong Growth Trajectory",
            "content": "Apple's services division shows continued momentum with subscription growth...",
            "sentiment_score": 0.7,
            "published_at": "2025-08-13T11:30:00Z",
            "source": "Wall Street Journal"
        }
    ]
}

logger = logging.getLogger(__name__)

class SentimentFeatureEngine:
    """
    Engine für Sentiment-basierte Features aus News-Daten
    """
    
    def __init__(self, database_pool: asyncpg.Pool):
        self.database_pool = database_pool
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def calculate_sentiment_features(self, symbol: str, lookback_days: int = 7) -> Dict[str, Any]:
        """
        Berechnet Sentiment-Features für ein Symbol
        """
        try:
            self.logger.info(f"Calculating sentiment features for {symbol}")
            
            # Hole News Daten (Mock für jetzt)
            news_data = await self._get_news_data(symbol, lookback_days)
            
            if not news_data:
                return {"error": f"No news data available for {symbol}"}
            
            # Berechne Sentiment Features
            features = await self._calculate_sentiment_indicators(news_data)
            
            # Speichere Features in DB
            await self._store_sentiment_features(symbol, features)
            
            return {
                "symbol": symbol,
                "feature_type": "sentiment",
                "features_calculated": len(features),
                "features": features,
                "news_count": len(news_data),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate sentiment features for {symbol}: {str(e)}")
            return {"error": str(e)}
    
    async def _get_news_data(self, symbol: str, lookback_days: int) -> List[Dict[str, Any]]:
        """
        Holt News-Daten für Symbol (Mock Implementation)
        """
        # Mock: Verwende vordefinierte News-Daten
        if symbol in MOCK_NEWS_DATA:
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Filtere nach Datum
            filtered_news = []
            for news in MOCK_NEWS_DATA[symbol]:
                news_date = datetime.fromisoformat(news["published_at"].replace('Z', '+00:00'))
                # Entferne Timezone-Info für Vergleich
                if news_date.replace(tzinfo=None) >= cutoff_date:
                    filtered_news.append(news)
            
            return filtered_news
        
        return []
    
    async def _calculate_sentiment_indicators(self, news_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Berechnet Sentiment-Indikatoren aus News-Daten
        """
        if not news_data:
            return {}
        
        sentiment_scores = [news["sentiment_score"] for news in news_data]
        
        # Basis Sentiment Features
        features = {
            # Durchschnittliche Sentiments
            "avg_sentiment": sum(sentiment_scores) / len(sentiment_scores),
            "weighted_sentiment": self._calculate_weighted_sentiment(news_data),
            
            # Sentiment Verteilung
            "positive_ratio": len([s for s in sentiment_scores if s > 0.1]) / len(sentiment_scores),
            "negative_ratio": len([s for s in sentiment_scores if s < -0.1]) / len(sentiment_scores),
            "neutral_ratio": len([s for s in sentiment_scores if -0.1 <= s <= 0.1]) / len(sentiment_scores),
            
            # Sentiment Volatilität
            "sentiment_volatility": self._calculate_sentiment_volatility(sentiment_scores),
            
            # Trend Features
            "sentiment_trend": self._calculate_sentiment_trend(news_data),
            
            # Volume Features
            "news_volume": len(news_data),
            "news_volume_ratio": min(len(news_data) / 10.0, 1.0),  # Normalisiert auf 10 News pro Woche
            
            # Source Diversity
            "source_diversity": len(set(news["source"] for news in news_data)) / len(news_data),
            
            # Zeitbasierte Features
            "recent_sentiment_1d": self._calculate_recent_sentiment(news_data, 1),
            "recent_sentiment_3d": self._calculate_recent_sentiment(news_data, 3),
            
            # Extreme Sentiment Features
            "max_positive_sentiment": max(sentiment_scores) if sentiment_scores else 0,
            "max_negative_sentiment": min(sentiment_scores) if sentiment_scores else 0,
            "sentiment_range": max(sentiment_scores) - min(sentiment_scores) if sentiment_scores else 0
        }
        
        return features
    
    def _calculate_weighted_sentiment(self, news_data: List[Dict[str, Any]]) -> float:
        """
        Berechnet zeitlich gewichtetes Sentiment (neuere News höher gewichtet)
        """
        if not news_data:
            return 0.0
        
        now = datetime.utcnow()
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for news in news_data:
            news_date = datetime.fromisoformat(news["published_at"].replace('Z', '+00:00'))
            # Gewichtung: exponentieller Abfall über Zeit
            days_old = (now - news_date.replace(tzinfo=None)).days
            weight = 2.0 ** (-days_old / 2.0)  # Halbwertszeit 2 Tage
            
            weighted_sum += news["sentiment_score"] * weight
            weight_sum += weight
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def _calculate_sentiment_volatility(self, sentiment_scores: List[float]) -> float:
        """
        Berechnet Sentiment-Volatilität
        """
        if len(sentiment_scores) < 2:
            return 0.0
        
        mean_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        variance = sum((s - mean_sentiment) ** 2 for s in sentiment_scores) / len(sentiment_scores)
        return variance ** 0.5
    
    def _calculate_sentiment_trend(self, news_data: List[Dict[str, Any]]) -> float:
        """
        Berechnet Sentiment-Trend über Zeit
        """
        if len(news_data) < 2:
            return 0.0
        
        # Sortiere nach Datum
        sorted_news = sorted(news_data, key=lambda x: x["published_at"])
        
        # Einfache lineare Regression
        n = len(sorted_news)
        sum_x = sum(range(n))
        sum_y = sum(news["sentiment_score"] for news in sorted_news)
        sum_xy = sum(i * news["sentiment_score"] for i, news in enumerate(sorted_news))
        sum_x2 = sum(i ** 2 for i in range(n))
        
        # Steigung der Trendlinie
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope
    
    def _calculate_recent_sentiment(self, news_data: List[Dict[str, Any]], days: int) -> float:
        """
        Berechnet durchschnittliches Sentiment der letzten N Tage
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_sentiments = []
        for news in news_data:
            news_date = datetime.fromisoformat(news["published_at"].replace('Z', '+00:00'))
            if news_date.replace(tzinfo=None) >= cutoff_date:
                recent_sentiments.append(news["sentiment_score"])
        
        return sum(recent_sentiments) / len(recent_sentiments) if recent_sentiments else 0.0
    
    async def _store_sentiment_features(self, symbol: str, features: Dict[str, float]):
        """
        Speichert Sentiment-Features in der Datenbank
        """
        try:
            async with self.database_pool.acquire() as conn:
                # Verwende TimescaleDB-optimierte Tabelle
                await conn.execute("""
                    INSERT INTO ml_features_ts 
                    (symbol, feature_type, calculation_timestamp, features_json, 
                     feature_count, quality_score, missing_values_ratio, outlier_count)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, 
                symbol, "sentiment", datetime.utcnow(), json.dumps(features),
                len(features), 0.85, 0.0, 0)
                
                self.logger.info(f"Stored sentiment features for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Failed to store sentiment features: {str(e)}")
    
    async def get_latest_sentiment_features(self, symbol: str) -> Dict[str, Any]:
        """
        Holt die neuesten Sentiment-Features für ein Symbol
        """
        try:
            async with self.database_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT features_json, feature_count, quality_score, calculation_timestamp
                    FROM ml_features_ts
                    WHERE symbol = $1 AND feature_type = 'sentiment'
                    ORDER BY calculation_timestamp DESC
                    LIMIT 1
                """, symbol)
                
                if not row:
                    return {"error": f"No sentiment features found for {symbol}"}
                
                features = json.loads(row['features_json'])
                
                return {
                    "symbol": symbol,
                    "feature_type": "sentiment",
                    "features": features,
                    "features_count": row['feature_count'],
                    "quality_score": float(row['quality_score']),
                    "calculated_at": row['calculation_timestamp'].isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get sentiment features for {symbol}: {str(e)}")
            return {"error": str(e)}

# Export für einfache Imports
__all__ = ['SentimentFeatureEngine']