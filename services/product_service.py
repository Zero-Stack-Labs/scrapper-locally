import logging
import json
import csv
from typing import List
from pathlib import Path
from models.product import Product
from repositories.product_repository import ProductRepository

logger = logging.getLogger(__name__)


class ProductService:
    
    def __init__(self):
        self.product_repository = ProductRepository()
    
    def process_scraped_files(self, file_paths: List[str]) -> dict:
        """
        Procesa archivos generados por el scraper y los guarda en base de datos
        """
        results = {
            'processed_files': 0,
            'total_products': 0,
            'successful_upserts': 0,
            'failed_upserts': 0,
            'errors': []
        }
        
        for file_path in file_paths:
            try:
                logger.info(f"Procesando archivo: {file_path}")
                products = self._load_products_from_file(file_path)
                
                if products:
                    batch_results = self._process_products_batch(products)
                    results['total_products'] += len(products)
                    results['successful_upserts'] += batch_results['successful']
                    results['failed_upserts'] += batch_results['failed']
                    results['errors'].extend(batch_results['errors'])
                
                results['processed_files'] += 1
                
            except Exception as e:
                error_msg = f"Error procesando archivo {file_path}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        logger.info(f"Procesamiento completado: {results}")
        return results
    
    def process_single_file(self, file_path: str) -> dict:
        """
        Procesa un solo archivo
        """
        return self.process_scraped_files([file_path])
    
    def _load_products_from_file(self, file_path: str) -> List[Product]:
        """
        Carga productos desde un archivo JSON o CSV
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        if file_path.suffix.lower() == '.json':
            return self._load_from_json(file_path)
        elif file_path.suffix.lower() == '.csv':
            return self._load_from_csv(file_path)
        else:
            raise ValueError(f"Formato de archivo no soportado: {file_path.suffix}")
    
    def _load_from_json(self, file_path: Path) -> List[Product]:
        """
        Carga productos desde archivo JSON
        """
        products = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            for item in data:
                product = self._dict_to_product(item)
                if product:
                    products.append(product)
        elif isinstance(data, dict):
            product = self._dict_to_product(data)
            if product:
                products.append(product)
        
        logger.info(f"Cargados {len(products)} productos desde {file_path}")
        return products
    
    def _load_from_csv(self, file_path: Path) -> List[Product]:
        """
        Carga productos desde archivo CSV
        """
        products = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                product = self._dict_to_product(row)
                if product:
                    products.append(product)
        
        logger.info(f"Cargados {len(products)} productos desde {file_path}")
        return products
    
    def _dict_to_product(self, data: dict) -> Product:
        """
        Convierte diccionario a objeto Product
        """
        try:
            external_id = data.get('external_id', '')
            name = data.get('name', '')
            brand = data.get('brand', '')
            
            if not external_id or not name:
                logger.warning(f"Producto incompleto, falta external_id o name: {data}")
                return None
            
            product = Product(external_id=external_id, name=name, brand=brand)
            
            product.provider_id = data.get('provider_id', 'www.locally.com')
            product.url = data.get('url', '')
            product.sku = data.get('sku', '')
            product.external_sell_price = float(data.get('external_sell_price', 0))
            product.currency = data.get('currency', '')
            product.condition = data.get('condition', '')
            product.description = data.get('description', '')
            product.page_number = data.get('page_number')
            product.store_id = data.get('store_id', '')
            product.lat = float(data.get('lat', 0))
            product.lng = float(data.get('lng', 0))
            product.zipcode = data.get('zipcode', '')
            product.store_name = data.get('store_name', '')
            
            if 'images' in data:
                if isinstance(data['images'], str):
                    product.images = data['images'].split('|') if data['images'] else []
                elif isinstance(data['images'], list):
                    product.images = data['images']
            
            if 'variants' in data:
                if isinstance(data['variants'], str):
                    try:
                        product.variants = json.loads(data['variants'])
                    except json.JSONDecodeError:
                        product.variants = []
                elif isinstance(data['variants'], list):
                    product.variants = data['variants']
            
            return product
            
        except Exception as e:
            logger.error(f"Error convirtiendo datos a Product: {e}, data: {data}")
            return None
    
    def _process_products_batch(self, products: List[Product]) -> dict:
        """
        Procesa un lote de productos con upsert
        """
        results = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for product in products:
            try:
                self.product_repository.upsert_product(product)
                results['successful'] += 1
            except Exception as e:
                error_msg = f"Error en upsert de producto {product.external_id}: {e}"
                logger.error(error_msg)
                results['failed'] += 1
                results['errors'].append(error_msg)
        
        return results 