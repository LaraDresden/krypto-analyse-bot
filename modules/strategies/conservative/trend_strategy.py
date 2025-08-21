"""
Conservative Trend Following Strategy.

Implementiert eine konservative Trend-Following Strategie mit:
- MA200/MA50 Trend-Analyse
- RSI Überkauft/Überverkauft Filter
- ATR-basiertes Risk Management
- Strenge Volatilitäts-Filter
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ...data_models import MarketData, TechnicalIndicators, NewsAnalysis, TradingDecision, TradingSignal
from ..base_strategy import BaseStrategy, StrategyPosition, StrategyMetrics
from .config import CONSERVATIVE_CONFIG, CONSERVATIVE_PARAMS, validate_conservative_config

class ConservativeTrendStrategy(BaseStrategy):
    """
    Conservative Trend Following Strategy.
    
    Diese Strategie fokussiert sich auf:
    1. Klare Trendbestätigung durch MA200/MA50
    2. Niedrige Volatilitäts-Präferenz
    3. Starkes Risk Management
    4. Langfristige Positionen
    """
    
    def __init__(self):
        super().__init__(
            name=CONSERVATIVE_PARAMS['name'],
            config=CONSERVATIVE_PARAMS
        )
        # Use conservative_config instead of self.config for strategy-specific parameters
        self.conservative_config = CONSERVATIVE_CONFIG
        self.validation_warnings = validate_conservative_config()
        
        if self.validation_warnings:
            for warning in self.validation_warnings:
                logging.warning(f"[ConservativeStrategy] {warning}")
    
    def analyze(self, symbol: str, market_data: MarketData, 
               indicators: TechnicalIndicators, 
               news: Optional[NewsAnalysis] = None) -> TradingDecision:
        """
        Hauptanalyse-Funktion für konservative Strategie.
        
        Args:
            market_data: Aktuelle Marktdaten
            indicators: Technische Indikatoren
            news: Optional News-Analyse
            
        Returns:
            TradingDecision mit Signal und Begründung
        """
        try:
            # 1. Trend-Analyse
            trend_signal = self._analyze_trend(indicators)
            
            # 2. Volatilitäts-Filter
            volatility_check = self._check_volatility(indicators)
            
            # 3. RSI-Filter
            rsi_signal = self._analyze_rsi(indicators)
            
            # 4. Volume-Bestätigung
            volume_check = self._check_volume(indicators)
            
            # 5. News-Filter (falls verfügbar)
            news_filter = self._analyze_news(news) if news else True
            
            # 6. Signal-Kombination
            final_signal = self._combine_signals(
                trend_signal, volatility_check, rsi_signal, 
                volume_check, news_filter, market_data.price
            )
            
            return final_signal
            
        except Exception as e:
            logging.error(f"[ConservativeStrategy] Analyse-Fehler: {e}")
            return TradingDecision(
                signal=TradingSignal.HOLD,
                confidence=0.0,
                reasoning=f"Analyse-Fehler: {str(e)}",
                timestamp=datetime.now(),
                stop_loss=None,
                take_profit=None
            )
    
    def _analyze_trend(self, indicators: TechnicalIndicators) -> Dict[str, any]:
        """Analysiert Trend basierend auf Moving Averages."""
        ma_50 = indicators.ma_50
        ma_200 = indicators.ma_200
        current_price = indicators.price
        
        # Trend-Bestimmung
        if ma_50 > ma_200 * (1 + self.config.min_trend_strength):
            trend_direction = "bullish"
            trend_strength = (ma_50 - ma_200) / ma_200
        elif ma_50 < ma_200 * (1 - self.config.min_trend_strength):
            trend_direction = "bearish" 
            trend_strength = (ma_200 - ma_50) / ma_200
        else:
            trend_direction = "neutral"
            trend_strength = 0.0
        
        # Preis-Position relativ zu MAs
        price_vs_ma50 = (current_price - ma_50) / ma_50
        price_vs_ma200 = (current_price - ma_200) / ma_200
        
        return {
            'direction': trend_direction,
            'strength': trend_strength,
            'price_vs_ma50': price_vs_ma50,
            'price_vs_ma200': price_vs_ma200,
            'ma_alignment': ma_50 > ma_200
        }
    
    def _check_volatility(self, indicators: TechnicalIndicators) -> bool:
        """Prüft ob Volatilität im akzeptablen Bereich liegt."""
        atr_percentage = indicators.atr_percentage
        return atr_percentage <= self.config.max_atr_percentage
    
    def _analyze_rsi(self, indicators: TechnicalIndicators) -> str:
        """Analysiert RSI für Überkauft/Überverkauft Signale."""
        rsi = indicators.rsi
        
        if rsi <= self.config.rsi_oversold:
            return "oversold"  # Potentieller Kauf
        elif rsi >= self.config.rsi_overbought:
            return "overbought"  # Potentieller Verkauf/Vermeidung
        else:
            return "neutral"
    
    def _check_volume(self, indicators: TechnicalIndicators) -> bool:
        """Prüft Volume-Bestätigung."""
        volume_ratio = getattr(indicators, 'volume_ratio', 1.0)
        return volume_ratio >= self.config.min_volume_ratio
    
    def _analyze_news(self, news: NewsAnalysis) -> bool:
        """Analysiert News für Risiko-Filter."""
        if not news:
            return True
        
        # Vermeide Positionen bei sehr negativen News
        if news.sentiment_score <= -5 and news.critical:
            return False
        
        return True
    
    def _combine_signals(self, trend: Dict, volatility_ok: bool, rsi: str, 
                        volume_ok: bool, news_ok: bool, current_price: float) -> TradingDecision:
        """Kombiniert alle Signale zu einer finalen Entscheidung."""
        
        reasons = []
        confidence = 0.0
        signal = TradingSignal.HOLD
        
        # Bullish Bedingungen
        if (trend['direction'] == 'bullish' and 
            trend['ma_alignment'] and
            volatility_ok and 
            rsi in ['oversold', 'neutral'] and
            volume_ok and 
            news_ok):
            
            signal = TradingSignal.BUY
            confidence = min(0.8, 0.4 + trend['strength'] * 2)
            reasons.extend([
                f"Bullisher Trend (MA50 > MA200)",
                f"Trend-Stärke: {trend['strength']:.2%}",
                f"Niedrige Volatilität ✓",
                f"Volume-Bestätigung ✓"
            ])
            
            if rsi == 'oversold':
                confidence += 0.1
                reasons.append("RSI überverkauft - gute Einstiegschance")
        
        # Bearish/Exit Bedingungen
        elif (trend['direction'] == 'bearish' or 
              rsi == 'overbought' or 
              not volatility_ok or
              not news_ok):
            
            signal = TradingSignal.SELL
            confidence = 0.6
            
            if trend['direction'] == 'bearish':
                reasons.append("Bärischer Trend (MA50 < MA200)")
            if rsi == 'overbought':
                reasons.append("RSI überkauft")
            if not volatility_ok:
                reasons.append("Hohe Volatilität - Risiko")
            if not news_ok:
                reasons.append("Negative News - Risiko")
        
        # Stop-Loss und Take-Profit berechnen
        stop_loss, take_profit = self._calculate_risk_levels(current_price, signal)
        
        return TradingDecision(
            signal=signal,
            confidence=confidence,
            reasoning=" | ".join(reasons) if reasons else "Keine klaren Signale",
            timestamp=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )
    
    def _calculate_risk_levels(self, current_price: float, signal: TradingSignal) -> tuple:
        """Berechnet Stop-Loss und Take-Profit Levels."""
        if signal not in [TradingSignal.BUY, TradingSignal.STRONG_BUY]:
            return None, None
        
        # Annahme: ATR wird separat übergeben oder geschätzt
        estimated_atr = current_price * 0.02  # 2% als Standard-ATR
        
        stop_loss = current_price - (estimated_atr * self.config.stop_loss_atr_multiplier)
        take_profit = current_price + (estimated_atr * self.config.stop_loss_atr_multiplier * self.config.take_profit_ratio)
        
        return stop_loss, take_profit
    
    def get_position_size(self, account_balance: float, current_price: float, 
                         stop_loss: float) -> float:
        """Berechnet optimale Position Size basierend auf Risk Management."""
        if not stop_loss or stop_loss >= current_price:
            return 0.0
        
        # Risk per Trade
        risk_per_share = current_price - stop_loss
        risk_amount = account_balance * self.config.max_position_size
        
        # Position Size
        shares = risk_amount / risk_per_share
        max_shares = (account_balance * self.config.max_position_size) / current_price
        
        return min(shares, max_shares)
    
    def update_position(self, position: StrategyPosition, market_data: MarketData,
                       indicators: TechnicalIndicators) -> Optional[TradingDecision]:
        """Update bestehende Position basierend auf aktuellen Marktdaten."""
        current_price = market_data.price
        
        # Stop-Loss Check
        if position.stop_loss and current_price <= position.stop_loss:
            return TradingDecision(
                signal=TradingSignal.SELL,
                confidence=1.0,
                reasoning="Stop-Loss ausgelöst",
                timestamp=datetime.now(),
                stop_loss=None,
                take_profit=None
            )
        
        # Take-Profit Check
        if position.take_profit and current_price >= position.take_profit:
            return TradingDecision(
                signal=TradingSignal.SELL,
                confidence=1.0,
                reasoning="Take-Profit erreicht",
                timestamp=datetime.now(),
                stop_loss=None,
                take_profit=None
            )
        
        # Trend-Reversal Check
        trend = self._analyze_trend(indicators)
        if trend['direction'] == 'bearish' and not trend['ma_alignment']:
            return TradingDecision(
                signal=TradingSignal.SELL,
                confidence=0.8,
                reasoning="Trend-Reversal: MA50 < MA200",
                timestamp=datetime.now(),
                stop_loss=None,
                take_profit=None
            )
        
        return None  # Position halten
    
    def get_strategy_info(self) -> Dict:
        """Gibt Informationen über die Strategie zurück."""
        return {
            **CONSERVATIVE_PARAMS,
            'config': {
                'max_position_size': self.config.max_position_size,
                'stop_loss_atr_multiplier': self.config.stop_loss_atr_multiplier,
                'take_profit_ratio': self.config.take_profit_ratio,
                'max_atr_percentage': self.config.max_atr_percentage,
                'rsi_oversold': self.config.rsi_oversold,
                'rsi_overbought': self.config.rsi_overbought
            },
            'validation_warnings': self.validation_warnings
        }
