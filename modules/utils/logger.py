"""
Erweiterte Logging-Infrastruktur für die Krypto-Analyse-Plattform.

Bietet strukturiertes Logging mit JSON-Format, Performance-Tracking,
Fehler-Sanitization und Multi-Environment Support.
"""

import logging
import json
import sys
import os
import traceback
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
import re

class SecuritySanitizer:
    """Sichere Behandlung von sensiblen Daten in Logs."""
    
    # Regex-Patterns für sensible Daten
    SENSITIVE_PATTERNS = [
        (r'(api_key|secret|token|key|password)[=:\s]*[a-zA-Z0-9_-]{10,}', '***REDACTED***'),
        (r'[a-zA-Z0-9+/]{20,}={0,2}', '***REDACTED***'),  # Base64-ähnliche Strings
        (r'\b[A-Za-z0-9]{32,}\b', '***REDACTED***'),      # Lange alphanumerische Strings
        (r'Bearer\s+[A-Za-z0-9_-]+', 'Bearer ***REDACTED***'),  # Bearer Tokens
    ]
    
    @classmethod
    def sanitize(cls, message: str) -> str:
        """Entfernt sensible Daten aus Log-Nachrichten."""
        if not isinstance(message, str):
            message = str(message)
        
        sanitized = message
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        
        return sanitized

class PerformanceTracker:
    """Verfolgt Performance-Metriken für Funktionen."""
    
    def __init__(self, operation_name: str, logger: logging.Logger):
        self.operation_name = operation_name
        self.logger = logger
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"🚀 Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            if exc_type:
                self.logger.error(f"❌ {self.operation_name} failed after {duration:.2f}s: {exc_val}")
            else:
                self.logger.info(f"✅ {self.operation_name} completed in {duration:.2f}s")

class StructuredFormatter(logging.Formatter):
    """JSON-basierter Formatter für strukturierte Logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Basis-Log-Struktur
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': SecuritySanitizer.sanitize(record.getMessage())
        }
        
        # Thread-Info für parallele Verarbeitung
        if hasattr(record, 'thread'):
            log_data['thread_id'] = record.thread
        
        # Exception-Info
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': SecuritySanitizer.sanitize(str(record.exc_info[1]) if record.exc_info[1] else ''),
                'traceback': SecuritySanitizer.sanitize(self.formatException(record.exc_info))
            }
        
        # Custom Felder
        for key, value in record.__dict__.items():
            if key.startswith('custom_'):
                log_data[key[7:]] = value  # Entferne 'custom_' Prefix
        
        return json.dumps(log_data, ensure_ascii=False)

class CryptoAnalysisLogger:
    """Zentrale Logging-Klasse für die Krypto-Analyse-Plattform."""
    
    def __init__(self, name: str = 'crypto_analysis', level: str = 'INFO'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Verhindere doppelte Handler
        if self.logger.handlers:
            return
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Konfiguriert verschiedene Log-Handler."""
        
        # Console Handler für Development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Einfaches Format für Console
        console_format = '%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        console_formatter = logging.Formatter(console_format)
        console_handler.setFormatter(console_formatter)
        
        # Security: Sanitize Console Output
        class SanitizingHandler(logging.StreamHandler):
            def emit(self, record):
                record.msg = SecuritySanitizer.sanitize(str(record.msg))
                super().emit(record)
        
        console_handler = SanitizingHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(console_handler)
        
        # File Handler für strukturierte Logs (optional)
        try:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(
                log_dir / 'crypto_analysis.log', 
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
            
            # Separater Handler für Errors
            error_handler = logging.FileHandler(
                log_dir / 'errors.log', 
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(error_handler)
            
        except Exception as e:
            # Fallback wenn File-Logging nicht möglich ist
            self.logger.warning(f"Could not setup file logging: {e}")
    
    def track_performance(self, operation_name: str) -> PerformanceTracker:
        """Context Manager für Performance-Tracking."""
        return PerformanceTracker(operation_name, self.logger)
    
    def log_api_call(self, api_name: str, endpoint: str, status_code: Optional[int] = None, 
                     duration: Optional[float] = None, **kwargs):
        """Spezielle Logging-Methode für API-Calls."""
        extra_data = {
            'custom_api_name': api_name,
            'custom_endpoint': SecuritySanitizer.sanitize(endpoint),
            'custom_status_code': status_code,
            'custom_duration': duration
        }
        extra_data.update({f'custom_{k}': v for k, v in kwargs.items()})
        
        if status_code and status_code >= 400:
            self.logger.error(f"API call failed: {api_name} -> {endpoint}", extra=extra_data)
        else:
            self.logger.info(f"API call successful: {api_name} -> {endpoint}", extra=extra_data)
    
    def log_trading_decision(self, coin: str, signal: str, confidence: float, reasoning: str):
        """Spezielle Logging-Methode für Trading-Entscheidungen."""
        extra_data = {
            'custom_coin': coin,
            'custom_signal': signal,
            'custom_confidence': confidence,
            'custom_reasoning': SecuritySanitizer.sanitize(reasoning)
        }
        self.logger.info(f"Trading decision: {coin} -> {signal} (confidence: {confidence:.2f})", extra=extra_data)
    
    def log_portfolio_update(self, portfolio_value: float, change_pct: float, positions_count: int):
        """Spezielle Logging-Methode für Portfolio-Updates."""
        extra_data = {
            'custom_portfolio_value': portfolio_value,
            'custom_change_percentage': change_pct,
            'custom_positions_count': positions_count
        }
        self.logger.info(f"Portfolio update: €{portfolio_value:.2f} ({change_pct:+.2f}%)", extra=extra_data)
    
    # Standard Logging-Methoden mit Security
    def debug(self, message: str, **kwargs):
        self.logger.debug(SecuritySanitizer.sanitize(message), extra=kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(SecuritySanitizer.sanitize(message), extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(SecuritySanitizer.sanitize(message), extra=kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs):
        self.logger.error(SecuritySanitizer.sanitize(message), exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, exc_info: bool = True, **kwargs):
        self.logger.critical(SecuritySanitizer.sanitize(message), exc_info=exc_info, extra=kwargs)

# Globale Logger-Instanz für einfachen Import
logger = CryptoAnalysisLogger()

# Health Check Funktionen
def write_health_check(success: bool, coins_analyzed: int, portfolio_value: float, 
                       error_msg: str = "", additional_metrics: Optional[Dict[str, Any]] = None) -> None:
    """Schreibt erweiterte Health-Check-Daten für Monitoring."""
    health_data = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "coins_analyzed": coins_analyzed,
        "portfolio_value": portfolio_value,
        "error_message": SecuritySanitizer.sanitize(error_msg),
        "version": "2.0.0",
        "system_info": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform
        }
    }
    
    if additional_metrics:
        health_data["metrics"] = additional_metrics
    
    try:
        with open('health.json', 'w', encoding='utf-8') as f:
            json.dump(health_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Health check written: Success={success}, Coins={coins_analyzed}, Value=€{portfolio_value:.2f}")
    except Exception as e:
        logger.error(f"Failed to write health check: {e}", exc_info=True)

# Exception Handler Decorator
def handle_exceptions(operation_name: str):
    """Decorator für robuste Fehlerbehandlung."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                with logger.track_performance(operation_name):
                    return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator

# Konfiguration aus Umgebungsvariablen
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
ENABLE_FILE_LOGGING = os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true'

# Re-initialisiere Logger mit Umgebungskonfiguration
if LOG_LEVEL in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    logger = CryptoAnalysisLogger(level=LOG_LEVEL)

__all__ = [
    'CryptoAnalysisLogger', 'logger', 'PerformanceTracker', 
    'SecuritySanitizer', 'write_health_check', 'handle_exceptions'
]
