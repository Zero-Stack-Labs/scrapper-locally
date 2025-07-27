import json
import requests
import time
import random
import uuid
import urllib3
from typing import List, Dict, Optional
from models.product import Product
from .footlocker_mapper import FootlockerMapper
from utils.logging_config import get_logger
from utils.proxy_manager import proxy_manager

# Disable SSL warnings for proxy requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__)

class FootlockerApiScraper:
    
    def __init__(self, base_url: str = "https://www.footlocker.com", x_kpsdk_ct: str = '', store_id: str = ''):
        self.base_url = base_url
        self.store_id = store_id
        self.api_url = f"{base_url}/zgw/search-core/products/v3/search"
        self.session = requests.Session()
        self.current_proxy = None
        
        # Generate more realistic headers that change per session
        self.headers = self._generate_realistic_headers(x_kpsdk_ct, base_url)
        
        # Set up proxy if available
        self._setup_proxy()
        
        # Configure session for container environment
        self._configure_session()

    def _generate_realistic_headers(self, x_kpsdk_ct: str, base_url: str) -> dict:
        """Generate realistic, randomized headers to avoid detection"""
        
        # Common user agents (rotate between them)
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        # Language preferences (rotate)
        languages = [
            'en-US,en;q=0.9',
            'en-US,en;q=0.9,es;q=0.8',
            'en-US,en;q=0.8,es;q=0.7',
            'en-GB,en;q=0.9,en-US;q=0.8'
        ]
        
        # Generate session-specific identifiers
        session_id = str(uuid.uuid4())[:8]
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': random.choice(languages),
            'accept-encoding': 'gzip, deflate, br',
            'user-agent': random.choice(user_agents),
            'x-kpsdk-ct': x_kpsdk_ct,
            'referer': f"{base_url}/category/brands/nike.htm",
            'origin': base_url,
            'sec-ch-ua': '"Google Chrome";v="138", "Chromium";v="138", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'connection': 'keep-alive',
            'x-session-id': session_id
        }
        
        return headers

    def _configure_session(self):
        """Configure session for container environment SSL handling"""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.debug("📝 Session configured with retry strategy")

    def _setup_proxy(self):
        """Set up proxy configuration for requests"""
        self.current_proxy = proxy_manager.get_proxy_config()
        if self.current_proxy:
            logger.info(f"🌐 Using proxy: {self.current_proxy.get('http', 'Unknown')}")
        else:
            logger.info("🔗 Using direct connection (no proxy)")

    def _rotate_proxy(self):
        """Rotate to next proxy if current one fails"""
        if self.current_proxy:
            proxy_manager.mark_proxy_failed(self.current_proxy)
        
        self.current_proxy = proxy_manager.get_proxy_config()
        if self.current_proxy:
            logger.info(f"🔄 Rotated to new proxy: {self.current_proxy.get('http', 'Unknown')}")
            
            # Generate new session headers with new proxy
            self._refresh_session_headers()
    
    def _refresh_session_headers(self):
        """Refresh session headers to appear as a new session"""
        x_kpsdk_ct = self.headers.get('x-kpsdk-ct', '')
        base_url = self.base_url
        self.headers = self._generate_realistic_headers(x_kpsdk_ct, base_url)
        
        # Create fresh session
        self.session.close()
        self.session = requests.Session()
        self._configure_session()
        logger.info("🔄 Generated fresh session with new headers")

    def _make_scraperapi_request(self, url: str) -> Optional[requests.Response]:
        """Make request using ScraperAPI's API endpoint for heavily protected sites"""
        api_key = self.current_proxy.get('scraperapi_key')
        
        # ScraperAPI API endpoint
        api_url = "http://api.scraperapi.com"
        
        params = {
            'api_key': api_key,
            'url': url,
            'ultra_premium': 'true',  # Required for heavily protected sites
            'render': 'false',        # We don't need JavaScript rendering for API calls
            'country_code': 'us',     # Use US IP addresses
            'session_number': random.randint(1, 100),  # Random session for rotation
        }
        
        # Add our custom headers as ScraperAPI parameters
        for key, value in self.headers.items():
            if key.lower() not in ['host', 'content-length', 'connection']:
                params[f'custom_header_{key}'] = value
        
        timeout = random.uniform(25, 35)
        
        logger.info(f"🌐 Making ScraperAPI Ultra Premium request to: {url}")
        logger.debug(f"🔧 ScraperAPI params: session={params['session_number']}, country={params['country_code']}")
        
        try:
            response = self.session.get(api_url, params=params, timeout=timeout)
            logger.info(f"📡 ScraperAPI response: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"❌ ScraperAPI request failed: {e}")
            return None

    def make_request(self, url: str, retry_count: int = 3) -> Optional[requests.Response]:
        """Make request with proxy rotation and retry logic"""
        for attempt in range(retry_count):
            try:
                logger.info(f"Making request to Footlocker API (attempt {attempt + 1}/{retry_count}): {url}")
                
                # Add random delay between requests to appear more human
                if attempt > 0:
                    delay = random.uniform(1.0, 3.0)
                    logger.info(f"⏱️ Adding random delay: {delay:.1f}s")
                    time.sleep(delay)
                
                # Handle different proxy modes
                if self.current_proxy and self.current_proxy.get('mode') == 'api':
                    # ScraperAPI API mode for heavily protected sites
                    response = self._make_scraperapi_request(url)
                else:
                    # Regular proxy mode
                    proxies = self.current_proxy if self.current_proxy and 'http' in self.current_proxy else None
                    
                    # Randomize timeout slightly to avoid detection patterns
                    timeout = random.uniform(25, 35)
                    
                    # SSL configuration for proxy requests in containers
                    ssl_verify = True
                    if proxies:
                        # Disable SSL verification for proxy requests in containers
                        # This is safe because the proxy handles SSL termination
                        ssl_verify = False
                        logger.debug("🔓 SSL verification disabled for proxy request")
                    
                    response = self.session.get(url, headers=self.headers, proxies=proxies, timeout=timeout, verify=ssl_verify)
                
                logger.info(f"Response received from API: {response.status_code}")
                
                # If successful, return response
                if response.status_code == 200:
                    return response
                
                # If 403 Forbidden, try rotating proxy
                elif response.status_code == 403:
                    logger.warning(f"🚫 403 Forbidden - IP blocked. Attempt {attempt + 1}/{retry_count}")
                    logger.error(f"API error response: {response.text[:200]}")
                    
                    # Try rotating proxy for next attempt
                    if attempt < retry_count - 1:
                        self._rotate_proxy()
                        time.sleep(2)  # Brief delay before retry
                        continue
                
                # Other error codes
                else:
                    logger.error(f"API error response: {response.text[:200]}")
                    return response
                    
            except requests.RequestException as e:
                logger.error(f"HTTP request error to API (attempt {attempt + 1}): {e}")
                
                # Try rotating proxy for next attempt
                if attempt < retry_count - 1:
                    self._rotate_proxy()
                    time.sleep(2)
                    continue
        
        logger.error(f"❌ All {retry_count} attempts failed for URL: {url}")
        return None

    def scrape_products_page(self, query: str = "Nike", current_page: int = 0, 
                           page_size: int = 100, sort: str = "relevance",
                           latitude: float = 0.0, longitude: float = 0.0, zipcode: str = '') -> List[Product]:
        
        query_encoded = f"%3A%3Acollection_id%3A{query.lower()}"
        url = f"{self.api_url}?query={query_encoded}&q={query}&currentPage={current_page}&sort={sort}&pageSize={page_size}&timestamp=3"
        if self.store_id:
            url += f"&storeID={self.store_id}"
        
        logger.info(f"Scraping page {current_page} from Footlocker API for query '{query}'")
        
        response = self.make_request(url)
        
        if not response:
            logger.error("Error getting data from Footlocker API: No response")
            return []
            
        if response.status_code != 200:
            logger.error(f"Error al obtener datos de API Footlocker: Status {response.status_code}")
            return []
        
        try:
            data = response.json()
            products_data = data.get('products', [])
            
            logger.info(f"Found {len(products_data)} products on page {current_page}")
            
            products = []
            for product_data in products_data:
                product = FootlockerMapper.map_api_product_to_product(
                    product_data, self.base_url,
                    store_id=self.store_id, latitude=latitude,
                    longitude=longitude, zipcode=zipcode
                )
                if product:
                    product.page_number = current_page
                    products.append(product)
            
            return products
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from Footlocker API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error processing products from Footlocker API: {e}")
            return []

    def scrape_all_products(self, query: str = "Nike", max_pages: int = None, page_size: int = 100, delay: int = 5,
                            latitude: float = 0.0, longitude: float = 0.0, zipcode: str = '') -> List[Product]:
        all_products = []
        current_page = 0
        
        while True:
            if max_pages is not None and current_page >= max_pages:
                logger.info(f"Reached maximum page limit ({max_pages}). Ending scraping.")
                break
                
            products = self.scrape_products_page(
                query, current_page, page_size,
                latitude=latitude, longitude=longitude, zipcode=zipcode
            )
            
            if not products:
                logger.info(f"No products found on page {current_page}. Ending scraping.")
                break
            
            all_products.extend(products)
            logger.info(f"Total products scraped so far: {len(all_products)}")
            
            current_page += 1
            
            # Apply delay between pages if not the last page and there are more pages to process
            if max_pages is None or current_page < max_pages:
                logger.info(f"Waiting {delay} seconds before next page...")
                time.sleep(delay)
        
        logger.info(f"Scraping de API completado. Total: {len(all_products)} productos")
        return all_products

    def close(self):
        self.session.close() 