"""
Conservative Trend Following Strategy - Simplified Implementation.

Diese vereinfachte Version implementiert die Grundfunktionalität
und kann schrittweise erweitert werden.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ...data_models import MarketData, TechnicalIndicators, NewsAnalysis, TradingDecision, TradingSignal
from ..base_strategy import BaseStrategy
from .config import CONSERVATIVE_CONFIG, CONSERVATIVE_PARAMS

class ConservativeTrendStrategy(BaseStrategy):
    """
    Vereinfachte Conservative Trend Following Strategy.
    
    Fokussiert auf:
    - MA50/MA200 Trend-Analyse
    - RSI Überkauft/Überverkauft
    - Einfaches Risk Management
    """
    
    def __init__(self):
        super().__init__(
            name=CONSERVATIVE_PARAMS['name'],
            config=CONSERVATIVE_PARAMS
        )
        self.strategy_config = CONSERVATIVE_CONFIG
        logging.info(f"Conservative Strategy initialized: {self.name}")
    
    def analyze(self, symbol: str, market_data: MarketData, 
               indicators: TechnicalIndicators, 
               news: Optional[NewsAnalysis] = None) -> TradingDecision:
        """
        Hauptanalyse-Funktion.
        """
        try:
            # 1. Trend-Check
            trend_bullish = self._is_trend_bullish(indicators)
            
            # 2. RSI-Check  
            rsi_signal = self._get_rsi_signal(indicators)
            
            # 3. Volatilitäts-Check
            volatility_ok = self._is_volatility_acceptable(indicators)
            
            # 4. News-Check
            news_ok = self._is_news_positive(news)
            
            # 5. Signal-Kombination
            signal, confidence, reasoning = self._combine_signals(
                trend_bullish, rsi_signal, volatility_ok, news_ok
            )
            
            # 6. Position Size berechnen
            position_size = self._calculate_position_size(signal, market_data.price)
            
            return TradingDecision(
                signal=signal,
                confidence=confidence,
                reasoning=reasoning,
                stop_loss=self._calculate_stop_loss(market_data.price, signal),
                take_profit=self._calculate_take_profit(market_data.price, signal),
                position_size=position_size
            )
            
        except Exception as e:
            logging.error(f"Conservative Strategy Error: {e}")
            return TradingDecision(
                signal=TradingSignal.HOLD,
                confidence=0.0,
                reasoning=f"Analysis Error: {str(e)}",
                stop_loss=None,
                take_profit=None,
                position_size=0.0
            )
    
    def _is_trend_bullish(self, indicators: TechnicalIndicators) -> bool:
        """Prüft ob Trend bullish ist (MA50 > MA200)."""
        return indicators.ma50 > indicators.ma200 * 1.01  # 1% Buffer
    
    def _get_rsi_signal(self, indicators: TechnicalIndicators) -> str:
        """Gibt RSI Signal zurück."""
        rsi = indicators.rsi
        if rsi <= 30:
            return "oversold"
        elif rsi >= 70:
            return "overbought"
        else:
            return "neutral"
    
    def _is_volatility_acceptable(self, indicators: TechnicalIndicators) -> bool:
        """Prüft ob Volatilität akzeptabel ist."""
        return indicators.atr_percentage <= 3.0  # Max 3% ATR
    
    def _is_news_positive(self, news: Optional[NewsAnalysis]) -> bool:
        """Prüft ob News positiv/neutral sind."""
        if not news:
            return True
        return news.sentiment_score >= -3 and not news.is_critical
    
    def _combine_signals(self, trend_bullish: bool, rsi_signal: str, 
                        volatility_ok: bool, news_ok: bool) -> tuple:
        """Kombiniert alle Signale zu einem finalen Signal."""
        
        reasons = []
        
        # BUY Bedingungen
        if (trend_bullish and rsi_signal in ['oversold', 'neutral'] and 
            volatility_ok and news_ok):
            
            signal = TradingSignal.BUY
            confidence = 0.7
            reasons.extend([
                "Bullish Trend (MA50 > MA200)",
                f"RSI {rsi_signal}",
                "Low Volatility",
                "Positive News"
            ])
            
            if rsi_signal == 'oversold':
                confidence += 0.1
                
        # SELL Bedingungen
        elif (not trend_bullish or rsi_signal == 'overbought' or 
              not volatility_ok or not news_ok):
            
            signal = TradingSignal.SELL
            confidence = 0.6
            
            if not trend_bullish:
                reasons.append("Bearish Trend")
            if rsi_signal == 'overbought':
                reasons.append("RSI Overbought")
            if not volatility_ok:
                reasons.append("High Volatility")
            if not news_ok:
                reasons.append("Negative News")
        
        # HOLD als Default
        else:
            signal = TradingSignal.HOLD
            confidence = 0.5
            reasons.append("No clear signals")
        
        reasoning = " | ".join(reasons)
        return signal, confidence, reasoning
    
    def _calculate_position_size(self, signal: TradingSignal, price: float) -> float:
        """Berechnet Position Size."""
        if signal in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            return self.strategy_config.max_position_size  # 5%
        return 0.0
    
    def _calculate_stop_loss(self, price: float, signal: TradingSignal) -> Optional[float]:
        """Berechnet Stop-Loss."""
        if signal in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            atr_estimate = price * 0.02  # 2% ATR estimate
            return price - (atr_estimate * self.strategy_config.stop_loss_atr_multiplier)
        return None
    
    def _calculate_take_profit(self, price: float, signal: TradingSignal) -> Optional[float]:
        """Berechnet Take-Profit."""
        if signal in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            atr_estimate = price * 0.02
            stop_distance = atr_estimate * self.strategy_config.stop_loss_atr_multiplier
            return price + (stop_distance * self.strategy_config.take_profit_ratio)
        return None
    
    def get_parameters(self) -> Dict[str, Any]:
        """Gibt Strategie-Parameter zurück."""
        return {
            'name': self.name,
            'config': {
                'max_position_size': self.strategy_config.max_position_size,
                'stop_loss_atr_multiplier': self.strategy_config.stop_loss_atr_multiplier,
                'take_profit_ratio': self.strategy_config.take_profit_ratio,
                'max_atr_percentage': self.strategy_config.max_atr_percentage,
                'rsi_oversold': self.strategy_config.rsi_oversold,
                'rsi_overbought': self.strategy_config.rsi_overbought
            }
        }
