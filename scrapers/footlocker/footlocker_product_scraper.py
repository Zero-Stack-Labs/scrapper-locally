import json
import requests
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from models.product import Product
from .footlocker_mapper import FootlockerMapper
from utils.logging_config import get_logger

logger = get_logger(__name__)

class FootlockerProductScraper:
    
    def __init__(self):
        self.base_url = "https://www.footlocker.com"
        self.session = requests.Session()
        
        # Configurar HTTPAdapter con pool de conexiones más grande
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(
            pool_connections=50,  # Número de pools de conexiones diferentes
            pool_maxsize=100,     # Máximo de conexiones por pool
            max_retries=retry_strategy,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'x-kpsdk-ct': '0FIHlutI2zbN6SvcJtiGSCCMcdxoBN0juj8S9fAwRtCgti12498OJht6h4PTD1dkJUT4G8vJuAXZ6gcRZ3xaHCVOdKNAvWDgwenJi2KHtp22pd2IGJhCXIOqRe9X6liospDknUoa83ZSa6AevjpEKUHe13Ii5ejpVLCg8Jff'
        }

    def make_request(self, url: str) -> Optional[requests.Response]:
        try:
            logger.debug(f"Haciendo petición a página de producto: {url}")
            response = self.session.get(url, headers=self.headers, timeout=30)
            logger.debug(f"Respuesta recibida de página: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error response de página: {response.text[:200]}")
            
            return response
        except requests.RequestException as e:
            logger.error(f"Error en petición HTTP a página: {e}")
            return None

    def get_product_details(self, product_id: str, delay: float = 1.0) -> Optional[Dict]:
        time.sleep(delay)
        
        url = f"{self.base_url}/product/~/{product_id}.html"
        
        logger.debug(f"Obteniendo detalles del producto: {product_id}")
        response = self.make_request(url)
        
        if not response or response.status_code != 200:
            logger.error(f"Error al obtener detalles del producto {product_id}: {response.status_code if response else 'No response'}")
            return None
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            json_ld_script = soup.find('script', {'id': 'productLdJson'})
            if not json_ld_script:
                logger.error(f"No se encontró JSON-LD para el producto {product_id}")
                return None
            
            product_data = json.loads(json_ld_script.string.strip())
            
            detailed_product = {
                'product_id': product_id,
                'name': product_data.get('name', ''),
                'brand': product_data.get('brand', ''),
                'model': product_data.get('model', ''),
                'sku': product_data.get('sku', ''),
                'description': product_data.get('description', ''),
                'image_url': product_data.get('image', ''),
                'condition': product_data.get('itemCondition', ''),
                'variants': []
            }
            
            offers = product_data.get('offers', [])
            if offers:
                detailed_product['variants'] = FootlockerMapper.map_product_details_to_variants(
                    offers, product_id, detailed_product['sku'], 
                    detailed_product['name'], detailed_product['image_url']
                )
            
            meta_description = soup.find('meta', {'name': 'description'})
            if meta_description and meta_description.get('content'):
                detailed_product['meta_description'] = meta_description.get('content')
            
            logger.debug(f"Detalles obtenidos para {product_id}: {len(detailed_product['variants'])} variantes")
            return detailed_product
            
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON-LD del producto {product_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener detalles del producto {product_id}: {e}")
            return None

    def get_product_details_batch(self, product_ids: List[str], max_workers: int = 3, 
                                delay: float = 1.0) -> List[Dict]:
        
        detailed_products = []
        failed_ids = []
        
        logger.info(f"Obteniendo detalles para {len(product_ids)} productos (max {max_workers} workers)...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_id = {
                executor.submit(self.get_product_details, product_id, delay): product_id
                for product_id in product_ids
            }
            
            for future in as_completed(future_to_id):
                product_id = future_to_id[future]
                try:
                    result = future.result()
                    if result:
                        detailed_products.append(result)
                        logger.debug(f"✅ Detalles obtenidos para: {product_id}")
                    else:
                        failed_ids.append(product_id)
                        logger.warning(f"❌ Falló obtener detalles para: {product_id}")
                except Exception as exc:
                    failed_ids.append(product_id)
                    logger.error(f'❌ Excepción al procesar producto {product_id}: {exc}')
        
        success_rate = len(detailed_products) / len(product_ids) * 100 if product_ids else 0
        logger.info(f"Detalles obtenidos exitosamente: {len(detailed_products)}/{len(product_ids)} productos ({success_rate:.1f}%)")
        
        if failed_ids:
            logger.warning(f"IDs fallidos (muestra): {failed_ids[:3]}")
        
        return detailed_products

    def close(self):
        self.session.close() 