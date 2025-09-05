"""Page scraper for product listing pages."""

import json
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from models.product import Product
from utils.logging_config import get_logger

logger = get_logger(__name__)

class PageScraper(BaseScraper):
    
    def __init__(self):
        super().__init__(use_proxy=True)
    
    def scrape_page(self, page: int) -> List[Product]:
        """Scrape products from a specific page."""
        url = f"https://www.locally.com/search/all/activities/depts?store={self.store_id}&sort=pop&page={page}"
        
        try:
            response = self.make_request(url)
            if not response:
                logger.error(f"No response received for page {page}")
                return []
            if response.status_code == 404:
                logger.info(f"Page {page} not found (404) - No more pages")
                return []
            elif response.status_code != 200:
                logger.warning(f"Error {response.status_code} on page {page}")
                return []
        except Exception as e:
            logger.error(f"Error making request to page {page}: {e}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        
        products = []
        
        for script in json_scripts:
            try:
                json_data = json.loads(script.string)
                
                if isinstance(json_data, list):
                    for item in json_data:
                        if item.get('@type') == 'Product':
                            product = Product.from_json_ld(item)
                            if product:
                                products.append(product)
                elif json_data.get('@type') == 'Product':
                    product = Product.from_json_ld(json_data)
                    if product:
                        products.append(product)
                        
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON-LD on page {page}: {e}")
                continue
        
        return products
    
    def get_product_links(self, page: int) -> List[str]:
        """Get product links from a specific page."""
        url = f"https://www.locally.com/search/all/activities/depts?store={self.store_id}&sort=pop&page={page}"
        
        try:
            response = self.make_request(url)
            if not response or response.status_code != 200:
                return []
        except Exception as e:
            logger.error(f"Error getting page {page}: {e}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        product_links = soup.find_all('a', href=True)
        
        for link in product_links:
            href = link['href']
            if '/product/' in href:
                if href.startswith('/'):
                    href = self.base_url + href
                links.append(href)
        
        return list(set(links))
    
    def _extract_product_from_json_ld(self, json_data: dict) -> Optional[Product]:
        """Extract product from JSON-LD data (fallback method)."""
        try:
            external_id = ""
            url = json_data.get('url', '')
            
            if url:
                import re
                match = re.search(r'/product/(\d+)/', url)
                if match:
                    external_id = match.group(1)
            
            if not external_id:
                external_id = json_data.get('sku', '') or json_data.get('@id', '')
            
            name = json_data.get('name', '')
            brand_data = json_data.get('brand', {})
            
            if isinstance(brand_data, dict):
                brand = brand_data.get('name', '')
            else:
                brand = str(brand_data) if brand_data else ''
            
            if not external_id or not name:
                return None
            
            product = Product(external_id, name, brand)
            product.url = url
            product.sku = json_data.get('sku', '')
            
            images = json_data.get('image', [])
            if isinstance(images, str):
                product.images = [images]
            elif isinstance(images, list):
                product.images = images
            
            offers = json_data.get('offers', [])
            if offers and isinstance(offers, list):
                first_offer = offers[0]
                try:
                    product.external_sell_price = float(first_offer.get('price', 0))
                except (ValueError, TypeError):
                    product.external_sell_price = 0.0
                product.currency = first_offer.get('priceCurrency', '')
                product.condition = first_offer.get('itemCondition', '')
            
            return product
            
        except Exception as e:
            logger.error(f"Error creating product from JSON-LD (fallback): {e}")
            return None
    
    def scrape_products_from_page(self, page: int = 0) -> List[Product]:
        """Legacy method for backward compatibility."""
        logger.info(f"Scraping page {page}...")
        
        products = self.scrape_page(page)
        
        if not products:
            logger.warning(f"Could not get any products from page {page}")
            return []
        
        logger.info(f"Found {len(products)} products on page {page}")
        return products 