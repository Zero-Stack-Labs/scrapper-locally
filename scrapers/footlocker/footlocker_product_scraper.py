import json
import re
import requests
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from models.product import Product
from models.variant import Variant
from .footlocker_mapper import FootlockerMapper
from utils.logging_config import get_logger

logger = get_logger(__name__)

class FootlockerProductScraper:
    
    def __init__(self, base_url: str = "https://www.footlocker.com", x_kpsdk_ct: str = ''):
        self.base_url = base_url
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
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-kpsdk-ct': x_kpsdk_ct
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
            
            detailed_variants = self._extract_detailed_variants(
                response.text, product_id, detailed_product['sku'], 
                detailed_product['name'], detailed_product['image_url']
            )
            if detailed_variants:
                detailed_product['variants'] = detailed_variants
                logger.debug(f"Extraídas {len(detailed_variants)} variantes detalladas con UPC")
            else:
                offers = product_data.get('offers', [])
                if offers:
                    detailed_product['variants'] = FootlockerMapper.map_product_details_to_variants(
                        offers, product_id, detailed_product['sku'], 
                        detailed_product['name'], detailed_product['image_url']
                    )
                    logger.debug(f"Usando variantes básicas de offers: {len(detailed_product['variants'])}")
            
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

    def _extract_detailed_variants(self, html_content: str, product_id: str, product_sku: str, product_name: str, fallback_image: str = "") -> List[Dict]:
        """
        Extrae las variantes de producto usando el método más robusto de balanceo de corchetes.
        """
        try:
            sizes_data = self._extract_variants_with_balancing(html_content, product_id)
            
            if not sizes_data:
                logger.warning(f"No se pudieron extraer variantes para {product_id}.")
                return []
            
            # El método de balanceo ya provee un array JSON, no se necesita limpieza adicional
            return self._process_sizes_data(sizes_data, product_id, product_sku, product_name, fallback_image)

        except Exception as e:
            logger.error(f"Error fatal al extraer variantes para {product_id}: {e}")
            return []

    def _extract_variants_with_balancing(self, html_content: str, product_id: str) -> List[Dict]:
        """
        Extrae el array 'sizes' usando un método de balanceo de corchetes.
        Este es el método más rápido y confiable.
        """
        try:
            start_pattern = '"sizes":['
            start_index = html_content.find(start_pattern)
            
            if start_index == -1:
                logger.debug(f"Patrón '\"sizes\":[' no encontrado para {product_id}")
                return []

            # Mover el índice al inicio del array
            start_index += len(start_pattern) - 1
            balance = 1
            current_index = start_index + 1
            
            while current_index < len(html_content) and balance > 0:
                char = html_content[current_index]
                if char == '[':
                    balance += 1
                elif char == ']':
                    balance -= 1
                current_index += 1
            
            if balance != 0:
                logger.warning(f"No se pudieron balancear los corchetes para {product_id}.")
                return []

            sizes_content = html_content[start_index:current_index]
            return json.loads(sizes_content)

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON extraído con balanceo para {product_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado en extracción con balanceo para {product_id}: {e}")
            return []

    def _process_sizes_data(self, sizes_data: List[Dict], product_id: str, product_sku: str, product_name: str, fallback_image: str) -> List[Dict]:
        """
        Procesa los datos de sizes extraídos directamente
        """
        try:
            # Validar que sizes_data sea una lista
            if not isinstance(sizes_data, list):
                logger.error(f"sizes_data no es una lista para {product_id}: {type(sizes_data)} - {sizes_data}")
                return []
            
            if len(sizes_data) == 0:
                logger.warning(f"sizes_data está vacío para {product_id}")
                return []
            
            variants = []
            
            for i, size_data in enumerate(sizes_data):
                # Validar que size_data sea un diccionario
                if not isinstance(size_data, dict):
                    logger.warning(f"Item {i} en sizes_data no es un diccionario para {product_id}: {type(size_data)} - {size_data}")
                    continue
                
                if not size_data.get('active', False):
                    continue
                
                variant_sku = size_data.get('id', '')
                upc = size_data.get('upc', '')
                
                if not variant_sku:
                    logger.debug(f"Item {i} sin variant_sku para {product_id}: {size_data}")
                    continue
                
                # Extraer atributos usando el mismo método que FootlockerMapper
                attributes = self._extract_variant_attributes(variant_sku, size_data)
                
                size = attributes.get('size', size_data.get('size', ''))
                color = attributes.get('color', '')
                
                # Construir nombre de variante igual que FootlockerMapper
                variant_name_parts = [product_name]
                if color:
                    variant_name_parts.append(f"Color: {color}")
                if size:
                    variant_name_parts.append(f"Size: {size}")
                
                variant_name = " - ".join(variant_name_parts)
                
                # Crear variant object con SKU como SKU y UPC como UPC
                variant = Variant(name=variant_name, upc=upc or variant_sku)
                variant.set_price(size_data.get('price', {}).get('salePrice', 0))
                variant.set_parent_info(product_id, product_sku)
                
                # Determinar stock status
                availability = 'InStock' if size_data.get('inventory', {}).get('inventoryAvailable', False) else 'OutOfStock'
                stock_status = "in_stock" if availability == 'InStock' else "out_of_stock"
                
                # Si el precio es <= 0, marcar como out_of_stock
                if variant.price <= 0:
                    stock_status = "out_of_stock"
                
                variant.set_stock_status(stock_status)
                
                # Añadir atributos localizados
                locally_attributes = {}
                if color:
                    locally_attributes['Color'] = color
                if size:
                    locally_attributes['Size'] = size
                
                # Añadir información básica de attributes
                for key, value in attributes.items():
                    if key not in ['color', 'size', 'variant_sku', 'base_sku']:
                        locally_attributes[key] = value
                
                variant.set_attributes(locally_attributes)
                
                # Convertir a dict y ajustar formato igual que FootlockerMapper
                variant_dict = variant.to_dict(fallback_image)
                variant_dict['product_id'] = variant_dict.pop('external_product_id')
                
                variants.append(variant_dict)
            
            return variants
            
        except Exception as e:
            logger.error(f"Error procesando sizes data para {product_id}: {e}")
            logger.debug(f"Tipo de sizes_data: {type(sizes_data)}")
            logger.debug(f"Contenido sizes_data (primeros 3 elementos): {sizes_data[:3] if isinstance(sizes_data, list) else sizes_data}")
            return []

    def _extract_variant_attributes(self, variant_sku: str, variant_info: dict = None) -> dict:
        attributes = {}
        
        # Extract size from SKU
        size_match = re.search(r'-(\d+\.?\d*)$', variant_sku)
        if size_match:
            attributes['size'] = size_match.group(1)
        
        # Extract color - first try from variant_info, then fallback to SKU mapping
        if variant_info and isinstance(variant_info, dict) and variant_info.get('color'):
            attributes['color'] = variant_info['color']
        
        # Extract gender from SKU prefix
        gender_patterns = {
            'W': 'Women',
            'M': 'Men', 
            'C': 'Kids',
            'D': 'Unisex'
        }
        
        first_char = variant_sku[0] if variant_sku else ''
        if first_char in gender_patterns:
            attributes['gender'] = gender_patterns[first_char]
        
        # Add SKU information
        attributes['variant_sku'] = variant_sku
        base_sku = re.sub(r'-\d+\.?\d*$', '', variant_sku)
        attributes['base_sku'] = base_sku
        
        # Extract model from base SKU
        if len(base_sku) >= 4:
            attributes['model'] = base_sku[1:5]
        
        return attributes

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