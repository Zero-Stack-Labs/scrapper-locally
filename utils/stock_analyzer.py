import json
import csv
from typing import List, Dict, Set
from collections import defaultdict
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import os
from models.product import Product
from repositories.product_repository import ProductRepository
from utils.logging_config import get_logger

load_dotenv()
logger = get_logger(__name__)

class StockAnalyzer:
    
    def __init__(self, output_dir: str = ".", enable_db_upsert: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enable_db_upsert = enable_db_upsert
        
        if self.enable_db_upsert:
            self.product_repository = ProductRepository()
            logger.info("StockAnalyzer inicializado con upsert automático habilitado")
        else:
            self.product_repository = None
    
    def generate_stock_analysis_files(self, all_products: List[Dict], locations: List[Dict]):
        if not all_products:
            return

        all_zipcodes = {location['zipcode'] for location in locations}
        
        logger.info(f"--- Analyzing stock across {len(locations)} locations ---")
        logger.info(f"Analyzing availability for zipcodes: {sorted(list(all_zipcodes))}")
        
        product_availability = self._analyze_product_availability(all_products, all_zipcodes)
        
        unified_products = self._create_unified_products(product_availability, all_zipcodes)
        
        self._save_unified_stock_file(unified_products)
        
        logger.info(f"Stock analysis completed: {len(unified_products)} products processed")
    
    def _analyze_product_availability(self, all_products: List[Dict], all_zipcodes: Set[str]) -> Dict:
        product_availability = defaultdict(lambda: {
            'locations': {},
            'available_zipcodes': set(),
            'in_stock_zipcodes': set(),
            'product_info': None
        })
        
        for product in all_products:
            external_id = product.get('external_id')
            zipcode = product.get('location_zipcode')
            
            if not external_id or not zipcode:
                continue
            
            product_availability[external_id]['locations'][zipcode] = product
            product_availability[external_id]['available_zipcodes'].add(zipcode)
            
            if not product_availability[external_id]['product_info']:
                product_availability[external_id]['product_info'] = product
            
            if self._has_in_stock_variants(product):
                product_availability[external_id]['in_stock_zipcodes'].add(zipcode)
        
        return dict(product_availability)
    
    def _has_in_stock_variants(self, product: Dict) -> bool:
        variants = product.get('variants', [])
        
        if not variants:
            return product.get('external_sell_price', 0) > 0
        
        for variant in variants:
            stock_status = variant.get('stock_status', '').lower()
            if stock_status in ['in stock', 'available', 'in_stock']:
                return True
        
        return False
    
    def _create_unified_products(self, product_availability: Dict, all_zipcodes: Set[str]) -> List[Dict]:
        unified_products = []
        
        for external_id, availability_info in product_availability.items():
            available_zipcodes = availability_info['available_zipcodes']
            in_stock_zipcodes = availability_info['in_stock_zipcodes']
            
            is_in_all_locations = available_zipcodes == all_zipcodes
            is_in_stock_everywhere = in_stock_zipcodes == available_zipcodes
            
            product_data = availability_info['product_info'].copy()
            
            if is_in_all_locations and is_in_stock_everywhere:
                product_data['stock_status'] = 'in_stock'
                product_data['availability_summary'] = {
                    'available_in_locations': len(available_zipcodes),
                    'total_locations': len(all_zipcodes),
                    'in_stock_locations': len(in_stock_zipcodes),
                    'available_zipcodes': sorted(list(available_zipcodes)),
                    'in_stock_zipcodes': sorted(list(in_stock_zipcodes))
                }
            else:
                product_data['stock_status'] = 'out_of_stock'
                
                out_of_stock_reasons = []
                if not is_in_all_locations:
                    missing_locations = all_zipcodes - available_zipcodes
                    out_of_stock_reasons.append(f"Not available in: {sorted(list(missing_locations))}")
                
                if not is_in_stock_everywhere:
                    out_of_stock_locations = available_zipcodes - in_stock_zipcodes
                    if out_of_stock_locations:
                        out_of_stock_reasons.append(f"Out of stock in: {sorted(list(out_of_stock_locations))}")
                
                product_data['availability_summary'] = {
                    'available_in_locations': len(available_zipcodes),
                    'total_locations': len(all_zipcodes),
                    'in_stock_locations': len(in_stock_zipcodes),
                    'available_zipcodes': sorted(list(available_zipcodes)),
                    'in_stock_zipcodes': sorted(list(in_stock_zipcodes)),
                    'out_of_stock_reasons': out_of_stock_reasons
                }
            
            product_data['available_zipcodes'] = sorted(list(available_zipcodes))
            product_data['in_stock_zipcodes'] = sorted(list(in_stock_zipcodes))
            product_data['all_zipcodes'] = sorted(list(all_zipcodes))
            
            unified_products.append(product_data)
        
        return unified_products
    
    def _save_unified_stock_file(self, unified_products: List[Dict]):
        in_stock_products = [p for p in unified_products if p.get('stock_status') == 'in_stock']
        out_of_stock_products = [p for p in unified_products if p.get('stock_status') == 'out_of_stock']
        
        self._save_json_file(in_stock_products, "products_in_stock.json")
        self._save_csv_file(in_stock_products, "products_in_stock.csv")
        
        self._save_json_file(out_of_stock_products, "products_out_of_stock.json")
        self._save_csv_file(out_of_stock_products, "products_out_of_stock.csv")
        
        if self.enable_db_upsert and self.product_repository:
            db_results = self._upsert_products_to_db(unified_products)
            if not db_results.get('skipped'):
                logger.info(f"DB upsert: {db_results['successful_upserts']} exitosos, {db_results['failed_upserts']} fallidos")
    
    def _upsert_products_to_db(self, products: List[Dict]) -> Dict:
        if not self.enable_db_upsert or not self.product_repository:
            return {"skipped": True, "reason": "DB upsert disabled"}
        
        results = {
            'successful_upserts': 0,
            'failed_upserts': 0,
            'errors': []
        }
        
        logger.info(f"Iniciando upsert de {len(products)} productos a la base de datos")
        
        for product_dict in products:
            try:
                product = self._dict_to_product(product_dict)
                if product:
                    self.product_repository.upsert_product(product)
                    results['successful_upserts'] += 1
                else:
                    results['failed_upserts'] += 1
                    results['errors'].append("No se pudo convertir producto a objeto Product")
            except Exception as e:
                error_msg = f"Error en upsert: {e}"
                logger.error(error_msg)
                results['failed_upserts'] += 1
                results['errors'].append(error_msg)
        
        logger.info(f"Upsert completado: {results['successful_upserts']} exitosos, {results['failed_upserts']} fallidos")
        return results
    
    def _dict_to_product(self, data: Dict) -> Product:
        try:
            external_id = data.get('external_id', '')
            name = data.get('name', '')
            brand = data.get('brand', '')
            
            if not external_id or not name:
                logger.warning(f"Producto incompleto, falta external_id o name")
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
            product.stock_status = data.get('stock_status', 'unknown')
            product.available_zipcodes = data.get('available_zipcodes', [])
            product.in_stock_zipcodes = data.get('in_stock_zipcodes', [])
            product.all_zipcodes = data.get('all_zipcodes', [])
            
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
            logger.error(f"Error convirtiendo datos a Product: {e}")
            return None
    
    def _save_json_file(self, products: List[Dict], filename: str):
        if not products:
            return

        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved {filename} ({len(products)} products)")
    
    def _save_csv_file(self, products: List[Dict], filename: str):
        if not products:
            return
        
        file_path = self.output_dir / filename
        
        csv_products = []
        for product in products:
            csv_product = self._prepare_product_for_csv(product)
            csv_products.append(csv_product)
        
        all_fields = set()
        for product in csv_products:
            all_fields.update(product.keys())
        
        fieldnames = sorted(list(all_fields))
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_products)
        
        logger.info(f"✅ Saved {filename} ({len(products)} products)")
    
    def _prepare_product_for_csv(self, product: Dict) -> Dict:
        csv_product = product.copy()
        
        if 'images' in csv_product and isinstance(csv_product['images'], list):
            csv_product['images_csv'] = '|'.join(csv_product['images'])
            del csv_product['images']
        
        if 'variants' in csv_product and isinstance(csv_product['variants'], list):
            csv_product['variants_json'] = json.dumps(csv_product['variants'], ensure_ascii=False)
            del csv_product['variants']
        
        if 'availability_summary' in csv_product and isinstance(csv_product['availability_summary'], dict):
            csv_product['availability_summary_json'] = json.dumps(csv_product['availability_summary'], ensure_ascii=False)
            del csv_product['availability_summary']
        
        return csv_product 