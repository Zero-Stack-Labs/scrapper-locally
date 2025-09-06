import requests
import os
from typing import Optional, Dict
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        self._cached_proxy = None
        
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
    
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        if not self.use_proxy:
            return None
        
        if self._cached_proxy:
            return self._cached_proxy
        
        username = os.getenv('OXYLABS_DATACENTER_USERNAME')
        password = os.getenv('OXYLABS_DATACENTER_PASSWORD')
        
        if not all([username, password]):
            logger.warning("Configuración de proxy incompleta.")
            return None
        
        self._cached_proxy = {
            'http': f'http://{username}:{password}@dc.oxylabs.io:8000',
            'https': f'http://{username}:{password}@dc.oxylabs.io:8000'
        }
        
        return self._cached_proxy
    
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
            # Add proxy configuration if enabled
            request_kwargs = kwargs.copy()
            if self.use_proxy:
                proxies = self._get_proxy()
                if proxies:
                    request_kwargs['proxies'] = proxies
            
            # Make the request
            response = self.session.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **request_kwargs
            )
            
            # Update cookies only if response has new cookies
            response_cookies = self.session.cookies.get_dict()
            if response_cookies:
                self.cookies.update(response_cookies)
            
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
            # Add proxy if enabled
            request_kwargs = {}
            if self.use_proxy:
                proxies = self._get_proxy()
                if proxies:
                    request_kwargs['proxies'] = proxies
            
            response = self.session.get(url, headers=temp_headers, timeout=30, **request_kwargs)
            
            if response.status_code == 200:
                response_cookies = self.session.cookies.get_dict()
                if response_cookies:
                    self.cookies.update(response_cookies)
                return True
            else:
                logger.error(f"Failed to initialize location. Status: {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Exception during location initialization: {e}")
            return False

    def close(self):
        self.session.close() 