import json
import requests
from typing import List, Dict, Optional
from urllib.parse import urlencode
from models.product import Product
from utils.logging_config import get_logger

logger = get_logger(__name__)

class FootlockerScraper:
    
    def __init__(self):
        self.base_url = "https://www.footlocker.com"
        self.api_url = "https://www.footlocker.com/zgw/search-core/products/v3/search"
        self.session = requests.Session()
        
        self.headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
        }
        
        self.cookies = {
            'ak_bmsc_fl_com-ssn': '0aVTi4UZ8jTgP8gePEGfjBxlNpVJpXON8Qz85HgmLhEt64zFF2pG8nTTmpDZkpw0oo2Btki2OZdkuRcK76HiPFMBw5Wvry1DLwRVpQsXzCJtAE4HYKoTqg69ioNAgHSp7hWFC82twuE6wczT31V6vLWlmzwYkXh6SycqvqqJQoy'
        }

    def make_request(self, url: str) -> Optional[requests.Response]:
        try:
            logger.info(f"Haciendo petición a Footlocker: {url}")
            response = self.session.get(url, headers=self.headers, cookies=self.cookies, timeout=30)
            logger.info(f"Respuesta recibida: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error response: {response.text[:200]}")
            
            return response
        except requests.RequestException as e:
            logger.error(f"Error en petición HTTP: {e}")
            return None

    def scrape_products(self, query: str = "Nike", current_page: int = 0, page_size: int = 250, sort: str = "relevance") -> List[Product]:
        
        query_encoded = f"%3A%3Acollection_id%3A{query.lower()}"
        url = f"{self.api_url}?query={query_encoded}&q={query}&currentPage={current_page}&sort={sort}&pageSize={page_size}&timestamp=3"
        
        logger.info(f"Scrapeando página {current_page} de Footlocker para query '{query}'")
        
        response = self.make_request(url)
        
        if not response:
            logger.error("Error al obtener datos de Footlocker: No response")
            return []
            
        if response.status_code != 200:
            logger.error(f"Error al obtener datos de Footlocker: Status {response.status_code}")
            return []
        
        try:
            data = response.json()
            products_data = data.get('products', [])
            
            logger.info(f"Encontrados {len(products_data)} productos en la página {current_page}")
            
            products = []
            for product_data in products_data:
                product = self._map_footlocker_to_product(product_data)
                if product:
                    product.page_number = current_page
                    products.append(product)
            
            return products
            
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON de Footlocker: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al procesar productos de Footlocker: {e}")
            return []

    def _map_footlocker_to_product(self, product_data: Dict) -> Optional[Product]:
        try:
            external_id = product_data.get('sku', '')
            name = product_data.get('name', '')
            
            if not external_id or not name:
                logger.warning(f"Producto sin ID o nombre: {product_data}")
                return None
            
            product = Product(external_id=external_id, name=name)
            
            product.provider_id = "www.footlocker.com"
            product.sku = product_data.get('baseProduct', external_id)
            product.brand = self._extract_brand_from_name(name)
            
            price_info = product_data.get('price', {})
            product.external_sell_price = price_info.get('value', 0.0)
            product.currency = "USD"
            
            original_price_info = product_data.get('originalPrice', {})
            if original_price_info and original_price_info.get('value', 0) > price_info.get('value', 0):
                product.external_compare_at_price = original_price_info.get('value')
                
            badges = product_data.get('badges', {})
            product.condition = "new" if badges.get('isNewProduct', False) else "unknown"
            
            images = product_data.get('images', [])
            if images:
                for img in images:
                    if img.get('format') == 'large' and img.get('url'):
                        product.images.append(img['url'])
            
            review_ratings = product_data.get('reviewRatings', {})
            if review_ratings:
                product.description = f"Rating: {review_ratings.get('rating', 0)}/5 ({review_ratings.get('reviews', 0)} reviews)"
            
            base_options = product_data.get('baseOptions', [])
            if base_options:
                for option in base_options:
                    selected = option.get('selected', {})
                    if selected.get('style'):
                        product.options.append({
                            'name': 'style',
                            'value': selected['style']
                        })
            
            if badges.get('isSale', False):
                product.tags.append({'name': 'sale', 'value': 'true'})
            if badges.get('isNewProduct', False):
                product.tags.append({'name': 'new', 'value': 'true'})
            if badges.get('isPromoted', False):
                product.tags.append({'name': 'promoted', 'value': 'true'})
            
            return product
            
        except Exception as e:
            logger.error(f"Error al mapear producto de Footlocker: {e}")
            return None

    def _extract_brand_from_name(self, name: str) -> str:
        common_brands = ['Nike', 'Adidas', 'Puma', 'Reebok', 'New Balance', 'Converse', 'Vans', 'Jordan']
        
        name_upper = name.upper()
        for brand in common_brands:
            if brand.upper() in name_upper:
                return brand
        
        first_word = name.split()[0] if name.split() else ""
        return first_word

    def scrape_all_products(self, query: str = "Nike", page_size: int = 250) -> List[Product]:
        all_products = []
        current_page = 0
        
        while True:
            products = self.scrape_products(query, current_page, page_size)
            
            if not products:
                logger.info(f"No se encontraron productos en la página {current_page}. Terminando scraping.")
                break
            
            all_products.extend(products)
            logger.info(f"Total de productos scrapeados hasta ahora: {len(all_products)}")
            
            current_page += 1
        
        logger.info(f"Scraping completado. Total: {len(all_products)} productos")
        return all_products

    def close(self):
        self.session.close()