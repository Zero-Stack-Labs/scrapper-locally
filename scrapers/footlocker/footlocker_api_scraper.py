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
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-kpsdk-ct': x_kpsdk_ct
        }

    def make_request(self, url: str) -> Optional[requests.Response]:
        try:
            logger.info(f"Haciendo petición a API Footlocker: {url}")
            response = self.session.get(url, headers=self.headers, timeout=30)
            logger.info(f"Respuesta recibida de API: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error response de API: {response.text[:200]}")
            
            return response
        except requests.RequestException as e:
            logger.error(f"Error en petición HTTP a API: {e}")
            return None

    def scrape_products_page(self, query: str = "Nike", current_page: int = 0, 
                           page_size: int = 100, sort: str = "relevance",
                           latitude: float = 0.0, longitude: float = 0.0, zipcode: str = '') -> List[Product]:
        
        query_encoded = f"%3A%3Acollection_id%3A{query.lower()}"
        url = f"{self.api_url}?query={query_encoded}&q={query}&currentPage={current_page}&sort={sort}&pageSize={page_size}&timestamp=3"
        if self.store_id:
            url += f"&storeID={self.store_id}"
        
        logger.info(f"Scrapeando página {current_page} de API Footlocker para query '{query}'")
        
        response = self.make_request(url)
        
        if not response:
            logger.error("Error al obtener datos de API Footlocker: No response")
            return []
            
        if response.status_code != 200:
            logger.error(f"Error al obtener datos de API Footlocker: Status {response.status_code}")
            return []
        
        try:
            data = response.json()
            products_data = data.get('products', [])
            
            logger.info(f"Encontrados {len(products_data)} productos en la página {current_page}")
            
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
            logger.error(f"Error al parsear JSON de API Footlocker: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al procesar productos de API Footlocker: {e}")
            return []

    def scrape_all_products(self, query: str = "Nike", max_pages: int = None, page_size: int = 100, delay: int = 5,
                            latitude: float = 0.0, longitude: float = 0.0, zipcode: str = '') -> List[Product]:
        all_products = []
        current_page = 0
        
        while True:
            if max_pages is not None and current_page >= max_pages:
                logger.info(f"Alcanzado límite máximo de páginas ({max_pages}). Terminando scraping.")
                break
                
            products = self.scrape_products_page(
                query, current_page, page_size,
                latitude=latitude, longitude=longitude, zipcode=zipcode
            )
            
            if not products:
                logger.info(f"No se encontraron productos en la página {current_page}. Terminando scraping.")
                break
            
            all_products.extend(products)
            logger.info(f"Total de productos scrapeados hasta ahora: {len(all_products)}")
            
            current_page += 1
            
            # Aplicar delay entre páginas si no es la última página y hay más páginas por procesar
            if max_pages is None or current_page < max_pages:
                logger.info(f"Esperando {delay} segundos antes de la siguiente página...")
                time.sleep(delay)
        
        logger.info(f"Scraping de API completado. Total: {len(all_products)} productos")
        return all_products

    def close(self):
        self.session.close() 