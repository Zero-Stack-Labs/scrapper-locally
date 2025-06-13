import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class BaseScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.locally.com"
        self.store_id: Optional[str] = None
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