"""Base scraper class with common configuration and session management."""

import requests
from typing import Dict, Optional


class BaseScraper:
    """Base scraper class with common headers, cookies, and session management."""
    
    def __init__(self):
        """Initialize base scraper with session and common configuration."""
        self.base_url = "https://www.locally.com"
        self.session = requests.Session()
        
        # Common headers for requests
        self.headers = {
            'accept': 'text/html, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9,es-US;q=0.8,es;q=0.7',
            'priority': 'u=1, i',
            'referer': 'https://www.locally.com/search/all/activities/depts?sort=pop',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # Cookies (can be updated as needed)
        self.cookies = {
            '_ga': 'GA1.1.1022862228.1749607930',
            '__pr.1nvc': 'Mr0rvLRf13',
            'lg_session_v1': 'eyJpdiI6IlwvSjJOajMxV0N6dWdpbTRxbjd2V2xrY2k4WUxpT1BoKzlXcGpwc3RrK2Q0PSIsInZhbHVlIjoidmFYbWVOcEtlcHVIZHNJaVJ0VDlxYVNQM0RXb2FkTTJnY2xVaW1WVWlNeTlZTHdDbVhOdWNSeXW9xZWZHRENaQmtaSFJzUm9xZ3o3S1RhdkdTdERHeGc9PSIsIm1hYyI6IjIwOTFiZDdiOThhOTRkOTc2NjJkZjQ2NzVhNTJmMTk1ZjM5Mzk0ZTJkMmM3NmRlMWFlMzhiZGE4MTZkYmMxNjAifQ%3D%3D'
        }
        
        # Store ID for this scraping session (will be set by the scraper)
        self.store_id = None
    
    def get_location_headers(self) -> Dict[str, str]:
        """Get headers specific for location initialization."""
        store_param = f"?store={self.store_id}&sort=pop" if self.store_id else "?sort=pop"
        return {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,es-US;q=0.8,es;q=0.7',
            'priority': 'u=1, i',
            'referer': f'https://www.locally.com/search/all/activities/depts{store_param}',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
        }
    
    def get_stock_headers(self, product_id: str) -> Dict[str, str]:
        """Get headers specific for stock API calls."""
        return {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9,es-US;q=0.8,es;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': f'https://www.locally.com/product/{product_id}/',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
    
    def initialize_location(self, lat: float = 30.838215, lng: float = -87.20102) -> bool:
        """
        Initialize the geographic location for the scraping session.
        
        Args:
            lat: Latitude coordinate
            lng: Longitude coordinate
            
        Returns:
            True if initialization was successful, False otherwise
        """
        url = f"https://www.locally.com/geo/point/{lat}/{lng}?switch_user_location=1&from=Locationswitcherinput.tsx+onSearchChange"
        
        headers = self.get_location_headers()
        
        try:
            response = self.session.get(url, headers=headers, cookies=self.cookies)
            print(f"Location initialization: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"Error initializing location: {e}")
            return False
    
    def make_request(self, url: str, headers: Optional[Dict[str, str]] = None, 
                    timeout: int = 10) -> Optional[requests.Response]:
        """
        Make a standard HTTP request with error handling.
        
        Args:
            url: URL to request
            headers: Optional custom headers (uses default if None)
            timeout: Request timeout in seconds
            
        Returns:
            Response object or None if request failed
        """
        if headers is None:
            headers = self.headers
        
        try:
            response = self.session.get(url, headers=headers, cookies=self.cookies, timeout=timeout)
            return response
        except Exception as e:
            print(f"Error making request to {url}: {e}")
            return None
    
    def update_cookies(self, new_cookies: Dict[str, str]):
        """Update session cookies."""
        self.cookies.update(new_cookies)
    
    def update_store_id(self, store_id: str):
        """Update the store ID for scraping."""
        self.store_id = store_id
        # Update referer header with new store ID
        if store_id:
            self.headers['referer'] = f'https://www.locally.com/search/all/activities/depts?store={store_id}&sort=pop'
        else:
            self.headers['referer'] = 'https://www.locally.com/search/all/activities/depts?sort=pop' 