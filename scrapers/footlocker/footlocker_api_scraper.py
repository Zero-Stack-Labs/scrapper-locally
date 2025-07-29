import json
import requests
import time
from typing import List, Dict, Optional
from models.product import Product
from .footlocker_mapper import FootlockerMapper
from utils.logging_config import get_logger

logger = get_logger(__name__)

class FootlockerApiScraper:
    
    def __init__(self, base_url: str = "https://www.footlocker.com", x_kpsdk_ct: str = '', store_id: str = ''):
        self.base_url = base_url
        self.store_id = store_id
        self.api_url = f"{base_url}/zgw/search-core/products/v3/search"
        self.session = requests.Session()
        
        self.headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-kpsdk-ct': x_kpsdk_ct
        }

    def make_request(self, url: str) -> Optional[requests.Response]:
        try:
            logger.info(f"Making request to Footlocker API: {url}")
            response = self.session.get(url, headers=self.headers, timeout=30)
            logger.info(f"Response received from API: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API error response: {response.text[:200]}")
            
            return response
        except requests.RequestException as e:
            logger.error(f"HTTP request error to API: {e}")
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