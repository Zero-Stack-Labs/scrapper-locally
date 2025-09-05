import requests
from typing import Optional, Dict
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.proxy_config import ProxyConfig

logger = logging.getLogger(__name__)

class BaseScraper:
    def __init__(self, use_proxy: bool = True):
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(
            pool_connections=2000,
            pool_maxsize=4000,
            max_retries=retry_strategy,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.base_url = "https://www.locally.com"
        self.store_id: Optional[str] = None
        self.use_proxy = use_proxy
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.cookies = {}

    def update_store_id(self, store_id: str):
        self.store_id = store_id

    def set_headers(self, headers: dict):
        self.headers.update(headers)
    
    def _get_random_proxy(self) -> Optional[Dict[str, str]]:
        if not self.use_proxy:
            return None
        
        try:
            proxy_config = ProxyConfig.get_random_oxylabs_config()
            
            endpoint = proxy_config.get('endpoint')
            username = proxy_config.get('username')
            password = proxy_config.get('password')
            
            if not all([endpoint, username, password]):
                logger.warning("Configuración de proxy incompleta para este request.")
                return None
            
            proxies = {
                'http': f'http://{username}:{password}@{endpoint}',
                'https': f'http://{username}:{password}@{endpoint}'
            }
            
            return proxies
            
        except Exception as e:
            logger.error(f"Error obteniendo proxy aleatorio: {e}")
            return None
    
    def disable_proxy(self):
        self.use_proxy = False
        logger.info("Proxy deshabilitado")

    def make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """
        Make a request using the session with proper headers and error handling.
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments for the request
            
        Returns:
            Response object or None if failed
        """
        try:
            # Use stored cookies if available
            if self.cookies:
                self.session.cookies.update(self.cookies)
            
            # Add proxy configuration if enabled (get random proxy for each request)
            request_kwargs = kwargs.copy()
            if self.use_proxy:
                proxies = self._get_random_proxy()
                if proxies:
                    request_kwargs['proxies'] = proxies
                    logger.debug(f"Usando proxy para request a: {url}")
            
            # Make the request
            response = self.session.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **request_kwargs
            )
            
            # Update cookies from response
            self.cookies.update(self.session.cookies.get_dict())
            
            logger.debug(f"Request to {url}: {response.status_code}")
            return response
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def initialize_location(self, lat: float, lng: float) -> bool:
        """
        Initializes the user's location by making a GET request to a specific endpoint.
        This is a crucial step for the scraper to see store-specific data.
        """
        url = f"{self.base_url}/geo/point/{lat}/{lng}?switch_user_location=1"
        
        referer_url = f"{self.base_url}/search/all/activities/depts?sort=pop"
        if self.store_id:
            referer_url = f"{self.base_url}/search/all/activities/depts?store={self.store_id}&sort=pop"
            
        temp_headers = self.headers.copy()
        temp_headers['referer'] = referer_url
        temp_headers['accept'] = '*/*'

        try:
            response = self.session.get(url, headers=temp_headers, timeout=15)
            
            if response.status_code == 200:
                self.cookies.update(self.session.cookies.get_dict())
                logger.debug(f"Location initialized for lat={lat}, lng={lng}")
                return True
            else:
                logger.error(f"Failed to initialize location. Status: {response.status_code}. URL: {url}")
                return False
        except requests.RequestException as e:
            logger.error(f"Exception during location initialization: {e}")
            return False

    def close(self):
        self.session.close() 