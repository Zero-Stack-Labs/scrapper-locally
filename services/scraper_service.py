from typing import List, Dict, Any
from repositories.scraper_repository import ScraperRepository
from utils.stock_analyzer import StockAnalyzer
from pathlib import Path
import json
from datetime import datetime
import csv
from models.product import Product
from repositories.product_repository import ProductRepository
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ScraperService:
    
    def __init__(self, output_dir: str):
        self.repository = ScraperRepository(output_dir)
        self.analyzer = StockAnalyzer()
        self.output_dir = Path(output_dir)
        self.product_repository = ProductRepository()
    
    def scrape_multiple_stores(self, store_configurations, scraper_params):
        """
        Scraper múltiples stores con configuraciones específicas.
        """
        results = []
        all_products = []
        
        for config in store_configurations:
            result = self.process_single_store(config, scraper_params)
            
            if result["success"]:
                all_products.extend(result["products"])
            
            results.append(result)
        
        analysis_result = self.generate_analysis(all_products, store_configurations)
        
        return {
            "results": results,
            "total_products": len(all_products),
            "analysis_generated": analysis_result["success"]
        }
    
    def process_single_store(self, store_config, scraper_params):
        """
        Procesa una sola tienda y retorna el resultado.
        """
        logger.info(f"Processing store {store_config['store_id']}")
        
        try:
            result = self.repository.scrape_single_store(
                store_id=store_config["store_id"],
                zipcode=store_config["zipcode"],
                lat=store_config["lat"],
                lng=store_config["lng"],
                store_name=store_config.get("store_name", ""),
                page_delay=scraper_params.get("page_delay", 2),
                max_product_workers=scraper_params.get("max_product_workers", 5),
                save_every=scraper_params.get("save_every", 10),
                max_pages=scraper_params.get("max_pages", None)
            )
            
            logger.info(f"Scraping successful for store {store_config['store_id']}: {result['products_scraped']} products")
            
            return {
                "success": True,
                "store_id": store_config["store_id"],
                "zipcode": store_config["zipcode"],
                "products_scraped": result["products_scraped"],
                "products": result["products"],
                "message": f"Successfully scraped {result['products_scraped']} products"
            }
            
        except Exception as e:
            logger.error(f"Error processing store {store_config['store_id']}: {e}", exc_info=True)
            return {
                "success": False,
                "store_id": store_config["store_id"],
                "zipcode": store_config["zipcode"],
                "error": str(e),
                "message": f"Failed to scrape store: {str(e)}"
            }
    
    def generate_analysis(self, all_products, store_configurations):
        """
        Genera análisis de stock y lo guarda en archivo.
        """
        try:
            if not all_products:
                return {
                    "success": False,
                    "message": "No products available for analysis"
                }
            
            stock_analysis = self.analyzer.analyze_stock_patterns(all_products)
            availability_by_store = self.analyzer.analyze_availability_by_store(all_products)
            
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "total_products_analyzed": len(all_products),
                "stores_analyzed": len(store_configurations),
                "stock_analysis": stock_analysis,
                "availability_by_store": availability_by_store,
                "store_configurations": [
                    {
                        "store_id": config["store_id"],
                        "zipcode": config["zipcode"]
                    }
                    for config in store_configurations
                ]
            }
            
            analysis_file = self.output_dir / f"stock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "message": f"Analysis saved to {analysis_file}",
                "analysis_file": str(analysis_file)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate analysis: {str(e)}"
            }
    
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