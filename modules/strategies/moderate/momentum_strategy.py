"""
Moderate Momentum Strategy - MACD + Bollinger Band Implementation.

Diese Strategie kombiniert:
- MACD Momentum-Signale
- Bollinger Band Breakout-Erkennung  
- Volume-Bestätigung
- Adaptive Volatilitäts-Anpassung
- Multi-Timeframe Trend-Filter
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from ...data_models import MarketData, TechnicalIndicators, NewsAnalysis, TradingDecision, TradingSignal
from ..base_strategy import BaseStrategy, TechnicalAnalysisHelpers
from .config import MODERATE_CONFIG, MODERATE_PARAMS

class ModerateMomentumStrategy(BaseStrategy):
    """
    Moderate Momentum Strategy basierend auf MACD und Bollinger Bands.
    
    Signal-Kombinationen:
    1. BUY: MACD bullish + BB oversold/neutral + volume confirmation + trend filter
    2. SELL: MACD bearish + BB overbought + risk management triggers
    3. HOLD: Unklare Signale oder hohe Volatilität
    """
    
    def __init__(self):
        super().__init__(
            name=MODERATE_PARAMS['name'],
            config=MODERATE_PARAMS
        )
        self.strategy_config = MODERATE_CONFIG
        logging.info(f"Moderate Momentum Strategy initialized: {self.name}")
    
    def analyze(self, symbol: str, market_data: MarketData, 
               indicators: TechnicalIndicators, 
               news: Optional[NewsAnalysis] = None) -> TradingDecision:
        """
        Hauptanalyse-Funktion für Momentum-basierte Signale.
        """
        try:
            # 1. MACD Momentum-Analyse
            macd_signal, macd_strength = self._analyze_macd_momentum(indicators)
            
            # 2. Bollinger Band Position & Breakout
            bb_signal, bb_strength = self._analyze_bollinger_bands(indicators)
            
            # 3. Volume-Bestätigung
            volume_confirmed = self._check_volume_confirmation(indicators)
            
            # 4. Volatilitäts-Check
            volatility_ok = self._is_volatility_acceptable(indicators)
            
            # 5. Trend-Filter (MA50 vs MA200)
            trend_direction = self._get_trend_direction(indicators)
            
            # 6. News-Sentiment Check
            news_sentiment_ok = self._check_news_sentiment(news)
            
            # 7. Signal-Kombination und Confidence-Berechnung
            final_signal, confidence, reasoning = self._combine_momentum_signals(
                macd_signal, macd_strength,
                bb_signal, bb_strength,
                volume_confirmed, volatility_ok,
                trend_direction, news_sentiment_ok
            )
            
            # 8. Position Size basierend auf Confidence und Volatilität
            position_size = self._calculate_adaptive_position_size(
                final_signal, confidence, indicators.atr_percentage
            )
            
            # 9. Risk Management Levels
            stop_loss = self._calculate_dynamic_stop_loss(
                market_data.price, final_signal, indicators.atr_percentage
            )
            take_profit = self._calculate_take_profit(
                market_data.price, stop_loss, final_signal
            )
            
            return TradingDecision(
                signal=final_signal,
                confidence=confidence,
                reasoning=reasoning,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size
            )
            
        except Exception as e:
            logging.error(f"Moderate Momentum Strategy Error: {e}")
            return TradingDecision(
                signal=TradingSignal.HOLD,
                confidence=0.0,
                reasoning=f"Analysis Error: {str(e)}",
                stop_loss=None,
                take_profit=None,
                position_size=0.0
            )
    
    def _analyze_macd_momentum(self, indicators: TechnicalIndicators) -> Tuple[str, float]:
        """Analysiert MACD für Momentum-Signale."""
        macd_hist = indicators.macd_histogram
        macd_line = indicators.macd
        macd_signal = indicators.macd_signal
        
        # Signal Strength basierend auf Histogram-Größe
        strength = min(abs(macd_hist) / self.strategy_config.macd_threshold, 1.0)
        
        # Bullish Conditions
        if (macd_hist > self.strategy_config.macd_threshold and 
            macd_line > macd_signal):
            # Check for momentum acceleration
            if macd_hist > 0:  # Strengthening momentum
                return "bullish_strong", min(strength * 1.2, 1.0)
            else:
                return "bullish", strength
        
        # Bearish Conditions  
        elif (macd_hist < -self.strategy_config.macd_threshold and
              macd_line < macd_signal):
            if macd_hist < 0:  # Strengthening bearish momentum
                return "bearish_strong", min(strength * 1.2, 1.0)
            else:
                return "bearish", strength
        
        # Neutral/Weak signals
        else:
            return "neutral", 0.3
    
    def _analyze_bollinger_bands(self, indicators: TechnicalIndicators) -> Tuple[str, float]:
        """Analysiert Bollinger Band Position für Entry/Exit Signale."""
        bb_position = indicators.bb_position
        
        # Oversold (near lower band) - potential buy opportunity
        if bb_position <= self.strategy_config.bb_oversold_threshold:
            strength = (self.strategy_config.bb_oversold_threshold - bb_position) / 20.0
            return "oversold", min(strength, 1.0)
        
        # Overbought (near upper band) - potential sell signal
        elif bb_position >= self.strategy_config.bb_breakout_threshold:
            # Unterscheide zwischen Breakout und Overbought
            if bb_position >= 95:  # Echter Breakout
                return "breakout", 0.8
            else:
                strength = (bb_position - self.strategy_config.bb_breakout_threshold) / 20.0
                return "overbought", min(strength, 1.0)
        
        # Middle Band Range - neutral
        elif (self.strategy_config.bb_oversold_threshold < bb_position < 
              self.strategy_config.bb_breakout_threshold):
            # Favor direction towards middle (50)
            if bb_position < 50:
                return "below_middle", 0.4
            else:
                return "above_middle", 0.4
        
        else:
            return "neutral", 0.3
    
    def _check_volume_confirmation(self, indicators: TechnicalIndicators) -> bool:
        """Prüft Volume-Bestätigung für Momentum-Signale."""
        if not self.strategy_config.volume_confirmation_enabled:
            return True
        
        volume_ratio = indicators.volume_ratio
        
        # Volume spike (sehr starke Bestätigung)
        if volume_ratio >= self.strategy_config.volume_spike_threshold:
            return True
        
        # Normale Volume-Bestätigung
        return volume_ratio >= self.strategy_config.min_volume_ratio
    
    def _is_volatility_acceptable(self, indicators: TechnicalIndicators) -> bool:
        """Prüft ob Volatilität im akzeptablen Bereich liegt."""
        atr_pct = indicators.atr_percentage
        return (self.strategy_config.min_atr_percentage <= atr_pct <= 
                self.strategy_config.max_atr_percentage)
    
    def _get_trend_direction(self, indicators: TechnicalIndicators) -> str:
        """Bestimmt Trend-Richtung basierend auf MA50/MA200."""
        if not self.strategy_config.enable_trend_filter:
            return "neutral"
        
        # Verwende TechnicalAnalysisHelpers für konsistente Trend-Erkennung
        if TechnicalAnalysisHelpers.is_bullish_trend(indicators):
            return "bullish"
        elif TechnicalAnalysisHelpers.is_bearish_trend(indicators):
            return "bearish"
        else:
            return "neutral"
    
    def _check_news_sentiment(self, news: Optional[NewsAnalysis]) -> bool:
        """Prüft News-Sentiment für Signal-Filter."""
        if not news:
            return True  # Keine News = neutral OK
        
        # Kritische News blockieren immer
        if self.strategy_config.critical_news_block and news.is_critical:
            return False
        
        # Sentiment-Threshold prüfen
        return news.sentiment_score >= self.strategy_config.min_news_sentiment
    
    def _combine_momentum_signals(self, macd_signal: str, macd_strength: float,
                                 bb_signal: str, bb_strength: float,
                                 volume_confirmed: bool, volatility_ok: bool,
                                 trend_direction: str, news_ok: bool) -> Tuple[TradingSignal, float, str]:
        """Kombiniert alle Signale zu finaler Entscheidung."""
        reasons = []
        base_confidence = 0.5
        
        # === BUY LOGIC ===
        if (macd_signal in ["bullish", "bullish_strong"] and 
            bb_signal in ["oversold", "below_middle"] and
            volatility_ok and news_ok):
            
            signal = TradingSignal.BUY
            
            # Confidence Calculation
            confidence = base_confidence
            confidence += macd_strength * 0.3  # MACD weight
            confidence += bb_strength * 0.2    # BB weight
            
            # Bonuses
            if volume_confirmed:
                confidence += 0.1
                reasons.append("Volume confirmed")
            if trend_direction == "bullish":
                confidence += 0.15
                reasons.append("Bullish trend")
            if macd_signal == "bullish_strong":
                confidence += 0.05
                reasons.append("Strong MACD momentum")
            
            reasons.extend([
                f"MACD {macd_signal}",
                f"BB {bb_signal}",
                "Volatility OK"
            ])
            
        # === STRONG BUY LOGIC ===  
        elif (macd_signal == "bullish_strong" and
              bb_signal == "oversold" and
              volume_confirmed and volatility_ok and
              trend_direction == "bullish" and news_ok):
            
            signal = TradingSignal.STRONG_BUY
            confidence = min(0.85 + macd_strength * 0.15, 0.95)
            reasons = ["Strong MACD + BB oversold", "Volume spike", "Bullish trend", "All filters OK"]
        
        # === SELL LOGIC ===
        elif (macd_signal in ["bearish", "bearish_strong"] and
              bb_signal in ["overbought", "above_middle"] and
              volatility_ok):
            
            signal = TradingSignal.SELL
            confidence = base_confidence
            confidence += macd_strength * 0.25
            confidence += bb_strength * 0.2
            
            if trend_direction == "bearish":
                confidence += 0.1
                reasons.append("Bearish trend")
            if not news_ok:
                confidence += 0.1
                reasons.append("Negative news")
            
            reasons.extend([
                f"MACD {macd_signal}",
                f"BB {bb_signal}"
            ])
        
        # === BREAKOUT LOGIC ===
        elif (bb_signal == "breakout" and 
              macd_signal in ["bullish", "bullish_strong"] and
              volume_confirmed):
            
            signal = TradingSignal.BUY
            confidence = 0.75  # High confidence for confirmed breakouts
            reasons = ["BB Breakout + MACD bullish", "Volume confirmation"]
        
        # === HOLD CONDITIONS ===
        else:
            signal = TradingSignal.HOLD
            confidence = 0.3
            
            # Identify hold reasons
            if not volatility_ok:
                reasons.append("High volatility")
            if not news_ok:
                reasons.append("Negative news")
            if not volume_confirmed and self.strategy_config.volume_confirmation_enabled:
                reasons.append("Low volume")
            if macd_signal == "neutral" and bb_signal == "neutral":
                reasons.append("No clear signals")
            
            if not reasons:
                reasons.append("Mixed signals")
        
        # Final confidence bounds and validation
        confidence = max(0.0, min(confidence, 1.0))
        
        # Apply minimum confidence thresholds
        if signal in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            if confidence < self.strategy_config.min_confidence_buy:
                signal = TradingSignal.HOLD
                reasons.append(f"Confidence too low ({confidence:.2f})")
        elif signal == TradingSignal.SELL:
            if confidence < self.strategy_config.min_confidence_sell:
                signal = TradingSignal.HOLD
                reasons.append(f"Confidence too low ({confidence:.2f})")
        
        reasoning = " | ".join(reasons)
        return signal, confidence, reasoning
    
    def _calculate_adaptive_position_size(self, signal: TradingSignal, 
                                        confidence: float, atr_percentage: float) -> float:
        """Berechnet adaptive Position Size basierend auf Confidence und Volatilität."""
        if signal not in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            return 0.0
        
        # Base size from confidence
        base_size = self.strategy_config.min_position_size + (
            (self.strategy_config.max_position_size - self.strategy_config.min_position_size) * confidence
        )
        
        # Volatility adjustment (reduce size for high volatility)
        volatility_factor = 1.0
        if atr_percentage > 3.0:  # High volatility
            volatility_factor = 0.7
        elif atr_percentage > 2.0:  # Medium-high volatility
            volatility_factor = 0.85
        
        # Strong buy bonus
        if signal == TradingSignal.STRONG_BUY:
            base_size *= 1.2
        
        adjusted_size = base_size * volatility_factor
        
        # Ensure bounds
        return max(self.strategy_config.min_position_size, 
                  min(adjusted_size, self.strategy_config.max_position_size))
    
    def _calculate_dynamic_stop_loss(self, price: float, signal: TradingSignal, 
                                   atr_percentage: float) -> Optional[float]:
        """Berechnet dynamischen Stop-Loss basierend auf ATR."""
        if signal not in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            return None
        
        # ATR-based distance
        atr_estimate = price * (atr_percentage / 100)
        stop_distance = atr_estimate * self.strategy_config.stop_loss_atr_multiplier
        
        # Tighter stop for high volatility
        if atr_percentage > 3.0:
            stop_distance *= 0.8
        
        return price - stop_distance
    
    def _calculate_take_profit(self, price: float, stop_loss: Optional[float], 
                             signal: TradingSignal) -> Optional[float]:
        """Berechnet Take-Profit basierend auf Risk/Reward Ratio."""
        if signal not in [TradingSignal.BUY, TradingSignal.STRONG_BUY] or not stop_loss:
            return None
        
        risk_distance = price - stop_loss
        reward_distance = risk_distance * self.strategy_config.take_profit_ratio
        
        return price + reward_distance
    
    def get_parameters(self) -> Dict[str, Any]:
        """Gibt aktuelle Strategie-Parameter zurück."""
        return {
            'name': self.name,
            'type': 'momentum',
            'risk_level': 'moderate',
            'config': {
                'max_position_size': self.strategy_config.max_position_size,
                'macd_threshold': self.strategy_config.macd_threshold,
                'bb_breakout_threshold': self.strategy_config.bb_breakout_threshold,
                'bb_oversold_threshold': self.strategy_config.bb_oversold_threshold,
                'stop_loss_atr_multiplier': self.strategy_config.stop_loss_atr_multiplier,
                'take_profit_ratio': self.strategy_config.take_profit_ratio,
                'min_confidence_buy': self.strategy_config.min_confidence_buy,
                'volume_confirmation_enabled': self.strategy_config.volume_confirmation_enabled,
                'trend_filter_enabled': self.strategy_config.enable_trend_filter
            },
            'features': [
                'MACD Momentum Analysis',
                'Bollinger Band Breakouts', 
                'Volume Confirmation',
                'Dynamic Position Sizing',
                'Adaptive Stop Loss',
                'Trend Filtering',
                'News Sentiment Integration'
            ]
        }
