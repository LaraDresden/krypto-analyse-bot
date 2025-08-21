"""
Datenquelle-Abstraktion für die Krypto-Analyse-Plattform.

Zentralisiert alle externen Datenquellen (Bitvavo, News APIs, Google Sheets)
mit robuster Fehlerbehandlung, Caching und Rate-Limiting.
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Protocol
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Lokale Imports
from ..data_models import MarketData, NewsAnalysis
from ..utils.logger import logger, handle_exceptions, SecuritySanitizer
from config import API_CONFIG, QUALITY_SOURCES, CRITICAL_KEYWORDS, get_api_credentials

@dataclass
class APIResponse:
    """Standardisierte API-Response-Struktur."""
    success: bool
    data: Any = None
    error_message: str = ""
    status_code: Optional[int] = None
    response_time: float = 0.0
    cached: bool = False

class DataProvider(Protocol):
    """Interface für alle Datenquellen."""
    
    def is_available(self) -> bool:
        """Prüft ob die Datenquelle verfügbar ist."""
        ...
    
    def get_rate_limit_delay(self) -> float:
        """Gibt die empfohlene Verzögerung zwischen Anfragen zurück."""
        ...

class BaseDataFetcher(ABC):
    """Abstrakte Basis-Klasse für alle Daten-Fetcher."""
    
    def __init__(self, name: str, timeout: int = 30):
        self.name = name
        self.timeout = timeout
        self.last_request_time = 0.0
        self.request_count = 0
        self.error_count = 0
        
    def _enforce_rate_limit(self, delay: float = 1.0):
        """Erzwingt Rate-Limiting zwischen Anfragen."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.debug(f"Rate limiting {self.name}: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    @handle_exceptions("api_request")
    def _make_request(self, url: str, params: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> APIResponse:
        """Macht einen HTTP-Request mit Fehlerbehandlung."""
        start_time = time.time()
        self.request_count += 1
        
        try:
            self._enforce_rate_limit()
            
            response = requests.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            # Log API Call
            logger.log_api_call(
                api_name=self.name,
                endpoint=url,
                status_code=response.status_code,
                duration=response_time
            )
            
            response.raise_for_status()
            
            return APIResponse(
                success=True,
                data=response.json(),
                status_code=response.status_code,
                response_time=response_time
            )
            
        except requests.exceptions.Timeout as e:
            self.error_count += 1
            error_msg = f"Timeout after {self.timeout}s"
            logger.error(f"{self.name} timeout: {error_msg}")
            return APIResponse(success=False, error_message=error_msg)
        
        except requests.exceptions.HTTPError as e:
            self.error_count += 1
            error_msg = f"HTTP {e.response.status_code}" if e.response else str(e)
            logger.error(f"{self.name} HTTP error: {error_msg}")
            return APIResponse(success=False, error_message=error_msg, status_code=e.response.status_code if e.response else None)
        
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            error_msg = SecuritySanitizer.sanitize(str(e))
            logger.error(f"{self.name} request error: {error_msg}")
            return APIResponse(success=False, error_message=error_msg)
        
        except Exception as e:
            self.error_count += 1
            error_msg = SecuritySanitizer.sanitize(str(e))
            logger.error(f"{self.name} unexpected error: {error_msg}")
            return APIResponse(success=False, error_message=error_msg)

class NewsAPIFetcher(BaseDataFetcher):
    """Fetcher für News API (newsapi.org)."""
    
    def __init__(self):
        super().__init__("NewsAPI", API_CONFIG['news_api_timeout'])
        credentials = get_api_credentials()
        self.api_key = credentials['news_api_key']
        self.base_url = "https://newsapi.org/v2"
    
    def is_available(self) -> bool:
        """Prüft ob News API verfügbar ist."""
        return self.api_key is not None
    
    def get_rate_limit_delay(self) -> float:
        """News API: 1000 requests/day = ~1 request alle 90 Sekunden."""
        return 2.0  # Konservativ
    
    @handle_exceptions("fetch_crypto_news")
    def fetch_crypto_news(self, search_terms: List[str], days_back: int = 1) -> APIResponse:
        """
        Holt Crypto-News für gegebene Suchbegriffe.
        
        Args:
            search_terms: Liste von Suchbegriffen
            days_back: Tage zurück in die Vergangenheit
            
        Returns:
            APIResponse mit News-Artikeln
        """
        if not self.is_available():
            return APIResponse(success=False, error_message="News API key not available")
        
        # Kombinierte Suche für Effizienz
        query = " OR ".join([f'"{term}"' for term in search_terms[:10]])  # Max 10 terms
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        params = {
            'q': query,
            'language': 'en',
            'from': from_date,
            'sortBy': 'relevancy',
            'pageSize': 50,
            'apiKey': self.api_key
        }
        
        url = f"{self.base_url}/everything"
        response = self._make_request(url, params)
        
        if response.success:
            articles = response.data.get('articles', [])
            # Filtere nur qualitativ hochwertige Quellen
            quality_articles = self._filter_quality_articles(articles)
            
            logger.info(f"NewsAPI: {len(quality_articles)}/{len(articles)} quality articles")
            response.data = {'articles': quality_articles}
        
        return response
    
    def _filter_quality_articles(self, articles: List[Dict]) -> List[Dict]:
        """Filtert Artikel nach Qualität der Quelle."""
        quality_articles = []
        
        for article in articles:
            url = article.get('url', '').lower()
            title = article.get('title') or ''
            description = article.get('description') or ''
            
            # Prüfe Qualitätsquellen
            is_quality_source = any(source in url for source in QUALITY_SOURCES)
            is_crypto_related = any(crypto_term in f"{title} {description}".lower() 
                                  for crypto_term in ['crypto', 'bitcoin', 'blockchain'])
            
            if is_quality_source or is_crypto_related:
                # Prüfe auf kritische Keywords
                is_critical = any(keyword.lower() in f"{title} {description}".lower() 
                                for keyword in CRITICAL_KEYWORDS)
                article['is_critical'] = is_critical
                quality_articles.append(article)
        
        return quality_articles

class FearGreedIndexFetcher(BaseDataFetcher):
    """Fetcher für Crypto Fear & Greed Index."""
    
    def __init__(self):
        super().__init__("FearGreedIndex", API_CONFIG['news_api_timeout'])
        self.base_url = "https://api.alternative.me"
    
    def is_available(self) -> bool:
        """Fear & Greed Index ist öffentlich verfügbar."""
        return True
    
    def get_rate_limit_delay(self) -> float:
        """Konservatives Rate-Limiting."""
        return 5.0
    
    @handle_exceptions("fetch_fear_greed_index")
    def fetch_fear_greed_index(self) -> APIResponse:
        """Holt den aktuellen Fear & Greed Index."""
        url = f"{self.base_url}/fng/"
        response = self._make_request(url)
        
        if response.success and response.data.get('data'):
            fng_data = response.data['data'][0]
            value = int(fng_data.get('value', 50))
            classification = fng_data.get('value_classification', 'Neutral')
            
            # Emoji-Mapping
            emoji_map = {
                'Extreme Fear': '😨', 'Fear': '😟', 'Neutral': '😐',
                'Greed': '😊', 'Extreme Greed': '🤑'
            }
            emoji = emoji_map.get(classification, '😐')
            
            processed_data = {
                'value': value,
                'classification': classification,
                'emoji': emoji,
                'timestamp': fng_data.get('timestamp', ''),
                'raw_data': fng_data
            }
            
            response.data = processed_data
            logger.info(f"Fear & Greed Index: {value} ({classification}) {emoji}")
        
        return response

class BitvavoPriceFetcher(BaseDataFetcher):
    """Fetcher für aktuelle Preise von Bitvavo (ohne Authentifizierung)."""
    
    def __init__(self):
        super().__init__("BitvavoPrices", 10)  # Kurzes Timeout für Preise
        self.base_url = "https://api.bitvavo.com/v2"
    
    def is_available(self) -> bool:
        """Bitvavo Public API ist immer verfügbar."""
        return True
    
    def get_rate_limit_delay(self) -> float:
        """Bitvavo: 1000 requests/minute = ~1 request/60ms."""
        return 0.1
    
    @handle_exceptions("fetch_ticker_prices")
    def fetch_ticker_prices(self, symbols: List[str]) -> APIResponse:
        """
        Holt aktuelle Preise für gegebene Symbole.
        
        Args:
            symbols: Liste von Währungssymbolen (z.B. ['BTC', 'ETH'])
            
        Returns:
            APIResponse mit Preisdaten
        """
        url = f"{self.base_url}/ticker/price"
        response = self._make_request(url)
        
        if response.success:
            all_prices = response.data
            
            # Filtere nur die gewünschten Symbole (EUR Paare)
            filtered_prices = {}
            for price_data in all_prices:
                market = price_data.get('market', '')
                if market.endswith('-EUR'):
                    symbol = market.replace('-EUR', '')
                    if symbol in symbols:
                        filtered_prices[symbol] = {
                            'price': float(price_data.get('price', 0)),
                            'market': market,
                            'timestamp': datetime.now()
                        }
            
            response.data = filtered_prices
            logger.info(f"Bitvavo prices: {len(filtered_prices)} symbols updated")
        
        return response

class GoogleSheetsFetcher(BaseDataFetcher):
    """Fetcher für Google Sheets Integration."""
    
    def __init__(self):
        super().__init__("GoogleSheets", API_CONFIG['gsheets_timeout'])
        credentials = get_api_credentials()
        self.credentials_json = credentials['google_credentials']
    
    def is_available(self) -> bool:
        """Prüft ob Google Credentials verfügbar sind."""
        return self.credentials_json is not None
    
    def get_rate_limit_delay(self) -> float:
        """Google Sheets: 300 requests/minute."""
        return 1.0
    
    @handle_exceptions("fetch_portfolio_history")
    def fetch_portfolio_history(self, days: int = 7) -> APIResponse:
        """
        Holt Portfolio-History aus Google Sheets.
        
        Args:
            days: Anzahl Tage für History
            
        Returns:
            APIResponse mit Portfolio-Daten
        """
        if not self.is_available():
            return APIResponse(success=False, error_message="Google credentials not available")
        
        try:
            import gspread
            
            # Parse credentials - Safe handling
            if not self.credentials_json:
                return APIResponse(success=False, error_message="Google credentials not available")
            
            credentials_dict = json.loads(self.credentials_json)
            gc = gspread.service_account_from_dict(credentials_dict)
            
            # Open spreadsheet
            spreadsheet = gc.open("Krypto-Analyse-DB")
            worksheet = spreadsheet.worksheet("Market_Data")
            
            # Get recent records
            try:
                records = worksheet.get_all_records()[-50:]  # Letzte 50 Einträge
            except Exception:
                # Fallback for header issues
                all_values = worksheet.get_all_values()
                if len(all_values) < 2:
                    return APIResponse(success=False, error_message="No data in sheet")
                
                records = []
                headers = all_values[0]
                for row in all_values[-50:]:
                    if len(row) >= len(headers):
                        record = dict(zip(headers, row))
                        records.append(record)
            
            # Process data
            portfolio_data = self._process_portfolio_history(records, days)
            
            return APIResponse(
                success=True, 
                data=portfolio_data,
                response_time=0.0  # Google Sheets doesn't provide timing
            )
            
        except Exception as e:
            error_msg = SecuritySanitizer.sanitize(str(e))
            logger.error(f"Google Sheets error: {error_msg}")
            return APIResponse(success=False, error_message=error_msg)
    
    def _process_portfolio_history(self, records: List[Dict], days: int) -> Dict:
        """Verarbeitet Portfolio-History-Daten."""
        portfolio_values = {}
        
        for record in records:
            timestamp_str = record.get('Zeitstempel', '')
            wert_str = record.get('Wert_EUR', '0')
            
            if timestamp_str and wert_str:
                try:
                    date = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').date()
                    wert = float(wert_str) if wert_str != '0' else 0
                    
                    if wert > 0:
                        if date not in portfolio_values:
                            portfolio_values[date] = 0
                        portfolio_values[date] += wert
                        
                except (ValueError, TypeError):
                    continue
        
        # Calculate performance metrics
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        current_value = portfolio_values.get(today, 0)
        yesterday_value = portfolio_values.get(yesterday, current_value)
        week_ago_value = portfolio_values.get(week_ago, current_value)
        
        change_24h = ((current_value - yesterday_value) / yesterday_value * 100) if yesterday_value > 0 else 0
        change_7d = ((current_value - week_ago_value) / week_ago_value * 100) if week_ago_value > 0 else 0
        
        return {
            'current_value': current_value,
            'change_24h': change_24h,
            'change_7d': change_7d,
            'daily_values': portfolio_values,
            'data_points': len(portfolio_values)
        }

class DataFetcherManager:
    """Manager für alle Data Fetcher."""
    
    def __init__(self):
        self.fetchers = {
            'news': NewsAPIFetcher(),
            'fear_greed': FearGreedIndexFetcher(),
            'prices': BitvavoPriceFetcher(),
            'portfolio': GoogleSheetsFetcher()
        }
        
        logger.info("DataFetcherManager initialized with fetchers: " + 
                   ", ".join(f"{name}({fetcher.is_available()})" 
                           for name, fetcher in self.fetchers.items()))
    
    def get_fetcher(self, name: str) -> Optional[BaseDataFetcher]:
        """Gibt einen Fetcher zurück."""
        return self.fetchers.get(name)
    
    def get_available_fetchers(self) -> Dict[str, bool]:
        """Gibt Status aller Fetcher zurück."""
        return {name: fetcher.is_available() for name, fetcher in self.fetchers.items()}
    
    def get_statistics(self) -> Dict[str, Dict[str, int]]:
        """Gibt Statistiken aller Fetcher zurück."""
        stats = {}
        for name, fetcher in self.fetchers.items():
            stats[name] = {
                'requests': fetcher.request_count,
                'errors': fetcher.error_count,
                'success_rate': (1 - fetcher.error_count / max(1, fetcher.request_count)) * 100
            }
        return stats

# Globale Manager-Instanz
data_manager = DataFetcherManager()

__all__ = [
    'DataProvider', 'BaseDataFetcher', 'NewsAPIFetcher', 'FearGreedIndexFetcher',
    'BitvavoPriceFetcher', 'GoogleSheetsFetcher', 'DataFetcherManager', 
    'data_manager', 'APIResponse'
]
