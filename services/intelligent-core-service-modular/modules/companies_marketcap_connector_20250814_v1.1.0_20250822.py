#!/usr/bin/env python3
"""
CompaniesMarketCap.com Data Connector
Event-Bus-First Web-Scraping Modul für Marktkapitalisierungsdaten
"""

import asyncio
import aiohttp
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import structlog
from dataclasses import dataclass
import time

# Add paths for imports
import sys

# Import Management - CLEAN ARCHITECTURE
from shared.import_manager_20250822_v1.0.1_20250822 import setup_aktienanalyse_imports
setup_aktienanalyse_imports()  # Replaces all sys.path.append statements

# FIXED: sys.path.append('/home/mdoehler/aktienanalyse-ökosystem/shared') -> Import Manager

from backend_base_module import BackendBaseModule
from event_bus import EventBusConnector, EventType


@dataclass
class CompanyMarketCapData:
    """Strukturierte Daten für ein Unternehmen"""
    rank: int
    name: str
    ticker: str
    market_cap: float  # in USD
    stock_price: float  # in USD
    daily_change_percent: float
    country: str
    currency: str = "USD"
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'rank': self.rank,
            'name': self.name,
            'ticker': self.ticker,
            'market_cap': self.market_cap,
            'stock_price': self.stock_price,
            'daily_change_percent': self.daily_change_percent,
            'country': self.country,
            'currency': self.currency,
            'last_updated': self.last_updated
        }


class CompaniesMarketCapConnector(BackendBaseModule):
    """
    Event-Bus-First Connector für CompaniesMarketCap.com
    Respectful Web-Scraping mit Rate-Limiting und Caching
    """
    
    def __init__(self, event_bus: EventBusConnector):
        super().__init__("companies_marketcap_connector", event_bus)
        
        # Configuration
        self.base_url = "https://companiesmarketcap.com"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate Limiting (optimized but respectful scraping)
        self.request_delay = 1.5  # 1.5 seconds between requests (optimized from 2.0)
        self.last_request_time = 0
        
        # Enhanced Caching with performance metrics
        self.cache: Dict[str, Any] = {}
        self.cache_duration = timedelta(hours=2)  # Extended to 2 hours for better performance
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Redis persistent cache for cross-session performance
        self.redis_cache_enabled = True
        self.redis_cache_prefix = "marketcap_cache:"
        self.redis_cache_ttl = 7200  # 2 hours in seconds
        
        # User-Agent for respectful scraping
        self.headers = {
            'User-Agent': 'Aktienanalyse-System/1.0 (+https://github.com/yourusername/aktienanalyse)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
    async def _initialize_module(self) -> bool:
        """Initialize HTTP session and test connectivity"""
        try:
            # Create optimized HTTP session
            connector = aiohttp.TCPConnector(
                limit=10,           # Increased from 5 for better throughput
                limit_per_host=4,   # Increased from 2 for parallel requests
                ttl_dns_cache=300,  # DNS cache for 5 minutes
                use_dns_cache=True,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(
                total=20,           # Reduced from 30 for faster timeouts
                connect=5,          # Connection timeout
                sock_read=10        # Socket read timeout
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            
            # Test connectivity
            await self._test_connectivity()
            
            # Optional: Warm up cache for common requests (async)
            asyncio.create_task(self._warm_up_cache())
            
            self.logger.info("CompaniesMarketCap connector initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to initialize CompaniesMarketCap connector", error=str(e))
            return False
    
    async def _subscribe_to_events(self):
        """Subscribe to relevant events"""
        await self.subscribe_to_event(
            EventType.MARKET_DATA_REQUEST, 
            self._handle_marketcap_request
        )
        await self.subscribe_to_event(
            EventType.MODULE_REQUEST,
            self._handle_company_lookup
        )
        
    async def _test_connectivity(self) -> bool:
        """Test if the website is accessible"""
        try:
            await self._rate_limited_request(f"{self.base_url}/")
            self.logger.info("CompaniesMarketCap connectivity test successful")
            return True
        except Exception as e:
            self.logger.error("CompaniesMarketCap connectivity test failed", error=str(e))
            return False
    
    async def _warm_up_cache(self):
        """Warm up cache with common requests in background"""
        try:
            self.logger.info("Starting cache warm-up")
            
            # Check if we already have cached data in Redis
            redis_cached = await self._get_redis_cache("top_companies_usa")
            if redis_cached:
                # Store in memory cache for faster access
                self._set_cache("top_companies_usa", redis_cached)
                self.logger.info("Cache warm-up: Loaded USA companies from Redis", count=len(redis_cached))
                return
            
            # If no cached data, warm up by fetching popular data
            self.logger.info("Cache warm-up: Fetching fresh data")
            companies = await self.get_top_companies("usa", 100)
            
            if companies:
                self.logger.info("Cache warm-up completed", companies_loaded=len(companies))
            else:
                self.logger.warning("Cache warm-up failed: No companies retrieved")
                
        except Exception as e:
            self.logger.warning("Cache warm-up error", error=str(e))
    
    async def _rate_limited_request(self, url: str) -> str:
        """Make HTTP request with rate limiting"""
        # Implement rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        
        self.last_request_time = time.time()
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    self.logger.debug("HTTP request successful", url=url, status=response.status)
                    return content
                else:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
        except Exception as e:
            self.logger.error("HTTP request failed", url=url, error=str(e))
            raise
    
    def _is_cached_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get('timestamp')
        if not cached_time:
            return False
        
        return datetime.now() - cached_time < self.cache_duration
    
    def _set_cache(self, cache_key: str, data: Any):
        """Set cache with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    async def _get_redis_cache(self, cache_key: str) -> Optional[List[CompanyMarketCapData]]:
        """Get cached data from Redis"""
        if not self.redis_cache_enabled or not hasattr(self.event_bus, 'redis'):
            return None
            
        try:
            redis_key = f"{self.redis_cache_prefix}{cache_key}"
            cached_json = await self.event_bus.redis.get(redis_key)
            
            if cached_json:
                cached_data = json.loads(cached_json)
                companies = []
                for item in cached_data:
                    companies.append(CompanyMarketCapData(**item))
                
                self.logger.debug("Redis cache hit", cache_key=cache_key)
                return companies
                
        except Exception as e:
            self.logger.warning("Redis cache read error", cache_key=cache_key, error=str(e))
            
        return None
    
    async def _set_redis_cache(self, cache_key: str, companies: List[CompanyMarketCapData]):
        """Set cached data in Redis"""
        if not self.redis_cache_enabled or not hasattr(self.event_bus, 'redis'):
            return
            
        try:
            redis_key = f"{self.redis_cache_prefix}{cache_key}"
            companies_data = [company.to_dict() for company in companies]
            cached_json = json.dumps(companies_data)
            
            await self.event_bus.redis.setex(redis_key, self.redis_cache_ttl, cached_json)
            self.logger.debug("Redis cache set", cache_key=cache_key, companies_count=len(companies))
            
        except Exception as e:
            self.logger.warning("Redis cache write error", cache_key=cache_key, error=str(e))

    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """Get cached data if valid with performance tracking"""
        if self._is_cached_valid(cache_key):
            self.cache_hits += 1
            self.logger.debug("Memory cache hit", cache_key=cache_key, hits=self.cache_hits)
            return self.cache[cache_key]['data']
        else:
            self.cache_misses += 1
            self.logger.debug("Memory cache miss", cache_key=cache_key, misses=self.cache_misses)
        return None
    
    async def _parse_company_table(self, html_content: str) -> List[CompanyMarketCapData]:
        """Parse HTML table and extract company data"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            companies = []
            
            # Find the marketcap table specifically
            table = soup.find('table', class_='marketcap-table')
            if not table:
                # Fallback to any table
                table = soup.find('table')
                if not table:
                    self.logger.warning("No marketcap table found in HTML content")
                    return companies
            
            # Find tbody and table rows (skip header)
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
            else:
                # Fallback to all rows, skip first (header)
                all_rows = table.find_all('tr')
                rows = all_rows[1:] if len(all_rows) > 1 else []
            
            self.logger.info(f"Found {len(rows)} data rows to parse")
            
            for row in rows:
                try:
                    # Skip ad rows and other non-data rows
                    if 'ad-tr' in row.get('class', []) or 'no-sort' in row.get('class', []):
                        continue
                        
                    cells = row.find_all('td')
                    if len(cells) < 7:  # Expected: fav, rank, name, market_cap, price, today, sparkline, country
                        continue
                    
                    # Extract rank from cells[1] (cells[0] is favorite icon)
                    rank_text = cells[1].get_text(strip=True)
                    rank = self._extract_number(rank_text)
                    
                    # Extract name and ticker from cells[2] (name-td)
                    name_cell = cells[2]
                    company_name_div = name_cell.find('div', class_='company-name')
                    company_code_div = name_cell.find('div', class_='company-code')
                    
                    if company_name_div:
                        name = company_name_div.get_text(strip=True)
                    else:
                        # Fallback - extract from name-div
                        name_div = name_cell.find('div', class_='name-div')
                        if name_div:
                            name = name_div.get_text(strip=True).split('\n')[0].strip()
                        else:
                            name = name_cell.get_text(strip=True)
                    
                    if company_code_div:
                        ticker = company_code_div.get_text(strip=True)
                    else:
                        # Extract ticker from name or fallback
                        ticker = self._extract_ticker(name_cell)
                    
                    # Market cap from cells[3]
                    market_cap_text = cells[3].get_text(strip=True)
                    market_cap = self._parse_market_cap(market_cap_text)
                    
                    # Stock price from cells[4]
                    price_text = cells[4].get_text(strip=True)
                    stock_price = self._extract_number(price_text)
                    
                    # Daily change from cells[5] (today column)
                    change_cell = cells[5]
                    change_text = change_cell.get_text(strip=True)
                    daily_change = self._parse_percentage(change_text)
                    
                    # Country from cells[7] (cells[6] is sparkline)
                    country_text = cells[7].get_text(strip=True) if len(cells) > 7 else "Unknown"
                    # Remove flag emoji and clean country name
                    country = country_text.split(' ')[-1] if ' ' in country_text else country_text
                    
                    # Clean up extracted data
                    if rank and name and market_cap > 0:
                        # Clean name - remove any residual ticker info
                        name_clean = name.replace(f"({ticker})", "").strip()
                        if not name_clean:
                            name_clean = name
                            
                        company = CompanyMarketCapData(
                            rank=int(rank),
                            name=name_clean,
                            ticker=ticker,
                            market_cap=market_cap,
                            stock_price=stock_price,
                            daily_change_percent=daily_change,
                            country=country,
                            last_updated=datetime.now().isoformat()
                        )
                        companies.append(company)
                        
                        # Log first few companies for debugging
                        if len(companies) <= 3:
                            self.logger.info("Parsed company", 
                                           rank=rank, name=name_clean, ticker=ticker, 
                                           market_cap=f"${market_cap:,.0f}", price=f"${stock_price:.2f}")
                        
                except Exception as e:
                    self.logger.warning("Error parsing table row", error=str(e), row_html=str(row)[:300])
                    continue
            
            self.logger.info("Successfully parsed company data", count=len(companies))
            return companies
            
        except Exception as e:
            self.logger.error("Error parsing HTML table", error=str(e))
            return []
    
    def _extract_ticker(self, cell) -> str:
        """Extract stock ticker from cell content"""
        try:
            # First, look for company-code div specifically
            company_code_div = cell.find('div', class_='company-code')
            if company_code_div:
                ticker_text = company_code_div.get_text(strip=True)
                # Clean ticker text (remove any rank info)
                ticker_clean = re.sub(r'^[\d\s]*', '', ticker_text).strip()
                if ticker_clean:
                    return ticker_clean
            
            # Look for ticker in parentheses in full text
            text = cell.get_text()
            ticker_match = re.search(r'\(([A-Z\.\-]{1,8})\)', text)
            if ticker_match:
                return ticker_match.group(1)
            
            # Look for ticker in class or data attributes
            ticker_elem = cell.find(['span', 'div'], class_=re.compile(r'ticker|symbol|code'))
            if ticker_elem:
                return ticker_elem.get_text(strip=True)
            
            # Extract from href in links (like 2222.SR for Saudi Aramco)
            link = cell.find('a')
            if link and link.get('href'):
                href = link.get('href', '')
                # Extract ticker-like patterns from URLs
                url_match = re.search(r'/([A-Z0-9\.\-]{1,8})/marketcap', href)
                if url_match:
                    return url_match.group(1).upper()
            
            # Fallback: extract uppercase/numeric ticker patterns
            ticker_pattern = re.search(r'\b([A-Z0-9\.\-]{2,8})\b', text)
            if ticker_pattern:
                potential_ticker = ticker_pattern.group(1)
                # Avoid common non-ticker words
                if potential_ticker not in ['USD', 'USA', 'LLC', 'INC', 'CORP']:
                    return potential_ticker
            
            return "UNKNOWN"
            
        except Exception:
            return "UNKNOWN"
    
    def _extract_number(self, text: str) -> float:
        """Extract numeric value from text"""
        try:
            # Remove all non-numeric characters except . and -
            cleaned = re.sub(r'[^\d.-]', '', text.replace(',', ''))
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    
    def _parse_market_cap(self, text: str) -> float:
        """Parse market cap with K, M, B, T suffixes"""
        try:
            # Remove currency symbols and clean text
            cleaned = re.sub(r'[^\d.KMBTkmbt-]', '', text.upper())
            
            # Extract number and suffix
            match = re.match(r'([\d.]+)([KMBT]?)', cleaned)
            if not match:
                return 0.0
            
            number = float(match.group(1))
            suffix = match.group(2)
            
            # Apply multiplier
            multipliers = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}
            multiplier = multipliers.get(suffix, 1)
            
            return number * multiplier
            
        except Exception:
            return 0.0
    
    def _parse_percentage(self, text: str) -> float:
        """Parse percentage change"""
        try:
            # Extract number and sign
            cleaned = re.sub(r'[^\d.%-]', '', text)
            number_match = re.search(r'([-]?[\d.]+)', cleaned)
            
            if number_match:
                return float(number_match.group(1))
            return 0.0
            
        except Exception:
            return 0.0
    
    async def get_top_companies(self, country: str = "usa", limit: int = 100) -> List[CompanyMarketCapData]:
        """Get top companies by market cap for a country with optimized caching"""
        start_time = datetime.now()
        
        # Optimized cache key strategy
        cache_key = f"top_companies_{country}"  # Remove limit from cache key for better reuse
        
        # Check memory cache first
        cached_data = self._get_cache(cache_key)
        if cached_data:
            cache_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info("Memory cache hit - returning cached data", 
                           cache_key=cache_key, 
                           response_time_ms=f"{cache_time:.2f}",
                           requested_limit=limit, 
                           cached_count=len(cached_data))
            return cached_data[:limit]
        
        # Check Redis cache if memory cache miss
        redis_cached_data = await self._get_redis_cache(cache_key)
        if redis_cached_data:
            # Store in memory cache for even faster subsequent access
            self._set_cache(cache_key, redis_cached_data)
            
            cache_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.info("Redis cache hit - returning cached data", 
                           cache_key=cache_key, 
                           response_time_ms=f"{cache_time:.2f}",
                           requested_limit=limit, 
                           cached_count=len(redis_cached_data))
            return redis_cached_data[:limit]
        
        try:
            # Use main page for all requests (most reliable)
            url = f"{self.base_url}/"
            
            # Fetch and parse data with timing
            fetch_start = datetime.now()
            html_content = await self._rate_limited_request(url)
            fetch_time = (datetime.now() - fetch_start).total_seconds() * 1000
            
            parse_start = datetime.now()
            companies = await self._parse_company_table(html_content)
            parse_time = (datetime.now() - parse_start).total_seconds() * 1000
            
            # Cache ALL companies for better reuse (both memory and Redis)
            if companies:
                self._set_cache(cache_key, companies)
                await self._set_redis_cache(cache_key, companies)
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.logger.info("Fetched and parsed market cap data", 
                           country=country, 
                           total_companies=len(companies),
                           returned_companies=min(len(companies), limit),
                           fetch_time_ms=f"{fetch_time:.2f}",
                           parse_time_ms=f"{parse_time:.2f}",
                           total_time_ms=f"{total_time:.2f}",
                           cache_hit_ratio=f"{self.cache_hits/(self.cache_hits + self.cache_misses)*100:.1f}%" if (self.cache_hits + self.cache_misses) > 0 else "0%")
            
            return companies[:limit]
            
        except Exception as e:
            error_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error("Error fetching company data", 
                            country=country, 
                            error=str(e),
                            error_time_ms=f"{error_time:.2f}")
            return []
    
    async def search_company(self, query: str) -> Optional[CompanyMarketCapData]:
        """Search for a specific company"""
        try:
            # Get top companies and search locally first
            companies = await self.get_top_companies("usa", 500)
            
            # Simple search by name or ticker
            query_upper = query.upper()
            for company in companies:
                if (query_upper in company.name.upper() or 
                    query_upper == company.ticker.upper()):
                    return company
            
            self.logger.info("Company not found in local data", query=query)
            return None
            
        except Exception as e:
            self.logger.error("Error searching for company", query=query, error=str(e))
            return None
    
    async def _handle_marketcap_request(self, event):
        """Handle market cap data requests via Event-Bus"""
        data = None
        request_id = None
        try:
            # Robust event data extraction
            if hasattr(event, 'data'):
                data = event.data
            elif hasattr(event, 'get'):
                data = event.get('data', {})
            else:
                data = event if isinstance(event, dict) else {}
            
            country = data.get('country', 'usa')
            limit = data.get('limit', 100)
            request_id = data.get('request_id')
            
            # Fetch company data
            companies = await self.get_top_companies(country, limit)
            
            # Convert to serializable format
            companies_data = [company.to_dict() for company in companies]
            
            # Publish response event
            await self.event_bus.publish({
                'event_type': 'market.data.response',
                'data': {
                    'request_id': request_id,
                    'success': True,
                    'companies': companies_data,
                    'total_count': len(companies_data),
                    'country': country,
                    'source': 'companiesmarketcap.com'
                },
                'source': 'companies_marketcap_connector'
            })
            
            self.logger.info("Market cap data request completed", 
                           request_id=request_id, count=len(companies_data))
            
        except Exception as e:
            self.logger.error("Error handling market cap request", error=str(e))
            
            # Publish error event with safe data access
            await self.publish_module_event(
                EventType.SYSTEM_ALERT_RAISED,
                {
                    'request_id': request_id if request_id else 'unknown',
                    'success': False,
                    'error': str(e),
                    'source': 'companiesmarketcap.com'
                }
            )
    
    async def _handle_company_lookup(self, event):
        """Handle individual company lookup requests"""
        data = None
        request_id = None
        query = ''
        try:
            # Robust event data extraction
            if hasattr(event, 'data'):
                data = event.data
            elif hasattr(event, 'get'):
                data = event.get('data', {})
            else:
                data = event if isinstance(event, dict) else {}
            
            query = data.get('query', '')
            request_id = data.get('request_id')
            
            # Search for company
            company = await self.search_company(query)
            
            if company:
                # Publish success response
                await self.event_bus.publish({
                    'event_type': 'marketcap.data.retrieved',
                    'data': {
                        'request_id': request_id,
                        'success': True,
                        'company': company.to_dict(),
                        'source': 'companiesmarketcap.com'
                    },
                    'source': 'companies_marketcap_connector'
                })
            else:
                # Company not found
                await self.event_bus.publish({
                    'event_type': 'marketcap.data.retrieved',
                    'data': {
                        'request_id': request_id,
                        'success': False,
                        'error': f'Company "{query}" not found',
                        'source': 'companiesmarketcap.com'
                    },
                    'source': 'companies_marketcap_connector'
                })
                
        except Exception as e:
            self.logger.error("Error handling company lookup", error=str(e))
    
    async def process_business_logic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main business logic processing"""
        try:
            operation = data.get('type', 'get_top_companies')
            
            if operation == 'get_top_companies':
                country = data.get('country', 'usa')
                limit = data.get('limit', 100)
                companies = await self.get_top_companies(country, limit)
                
                return {
                    'success': True,
                    'companies': [company.to_dict() for company in companies],
                    'total_count': len(companies)
                }
                
            elif operation == 'search_company':
                query = data.get('query', '')
                company = await self.search_company(query)
                
                if company:
                    return {
                        'success': True,
                        'company': company.to_dict()
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Company "{query}" not found'
                    }
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown operation: {operation}'
                }
                
        except Exception as e:
            self.logger.error("Error in business logic processing", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _cleanup_module(self):
        """Cleanup resources with performance metrics logging"""
        try:
            # Log final performance metrics
            total_requests = self.cache_hits + self.cache_misses
            if total_requests > 0:
                hit_ratio = (self.cache_hits / total_requests) * 100
                self.logger.info("Final performance metrics",
                               cache_hits=self.cache_hits,
                               cache_misses=self.cache_misses,
                               cache_hit_ratio=f"{hit_ratio:.1f}%",
                               cached_entries=len(self.cache))
            
            if self.session:
                await self.session.close()
                
            # Clear cache and reset metrics
            self.cache.clear()
            self.cache_hits = 0
            self.cache_misses = 0
            
            await super()._cleanup_module()
        except Exception as e:
            self.logger.warning("Error during cleanup", error=str(e))