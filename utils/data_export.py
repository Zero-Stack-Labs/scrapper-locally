"""Data export utilities for saving scraped data."""

import json
import pandas as pd
import os
from typing import List, Dict, Optional
from pathlib import Path
import logging
from dotenv import load_dotenv
from models.product import Product
from repositories.product_repository import ProductRepository

load_dotenv()
logger = logging.getLogger(__name__)

class DataExporter:
    def __init__(self, output_dir: str = ".", filename_suffix: str = "", enable_db_upsert: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.filename_suffix = filename_suffix
        self.enable_db_upsert = enable_db_upsert
        
        if self.enable_db_upsert:
            self.product_repository = ProductRepository()
            logger.info("DataExporter inicializado con upsert automático habilitado")
        else:
            self.product_repository = None
    
    def save_products_json(self, products: List[Dict], filename: str = "products.json"):
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(products)} products to {filepath}")
    
    def save_products_csv(self, products: List[Dict], filename: str = "products.csv"):
        if not products:
            logger.warning(f"No products to save to {filename}")
            return
        
        filepath = self.output_dir / filename
        
        # Convert to DataFrame
        df = pd.DataFrame(products)
        
        # Save to CSV
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Saved {len(products)} products to {filepath}")
    
    def _dict_to_product(self, data: Dict) -> Optional[Product]:
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
    
    def _upsert_products_to_db(self, products: List[Dict]) -> Dict:
        """
        Hace upsert de productos a la base de datos
        """
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
    
    def save_unified_products(self, products: List[Dict]):
        if not products:
            return
        
        logger.info(f"Saving {len(products)} unified products...")
        
        json_filename = f"products_{self.filename_suffix}.json" if self.filename_suffix else "products.json"
        csv_filename = f"products_{self.filename_suffix}.csv" if self.filename_suffix else "products.csv"
        
        self.save_products_json(products, json_filename)
        
        csv_products = [self._convert_for_csv(p) for p in products]
        
        self.save_products_csv(csv_products, csv_filename)
        
        logger.info("Unified products saved successfully")
    
    def save_general_products(self, products: List[Dict]):
        if not products:
            return
        
        logger.info(f"Saving {len(products)} general products...")
        
        self.save_products_json(products, "products_general.json")
        
        self.save_products_csv(products, "products_general.csv")
        
        logger.info("General products saved successfully")
    
    def save_detailed_products(self, products: List[Dict]):
        if not products:
            return
        
        logger.info(f"Saving {len(products)} detailed products...")
        
        self.save_products_json(products, "products_details.json")
        
        csv_products = []
        for product in products:
            if hasattr(product, 'to_dict_for_csv'):
                csv_product = product.to_dict_for_csv()
            else:
                csv_product = self._convert_for_csv(product)
            csv_products.append(csv_product)
        
        self.save_products_csv(csv_products, "products_details.csv")
        
        logger.info("Detailed products saved successfully")
    
    def _convert_for_csv(self, product: Dict) -> Dict:
        csv_product = product.copy()
        
        if 'images' in csv_product and isinstance(csv_product['images'], list):
            csv_product['images_csv'] = '|'.join(csv_product['images'])
            del csv_product['images']
        
        if 'variants' in csv_product and isinstance(csv_product['variants'], list):
            csv_product['variants_json'] = json.dumps(csv_product['variants'], ensure_ascii=False)
            del csv_product['variants']
        
        return csv_product
    
    def print_unified_statistics(self, products: List[Dict]):
        logger.info("--- UNIFIED SCRAPING STATISTICS ---")
        if not products:
            logger.info("No products to analyze.")
            return

        prices = [p.get('external_sell_price', 0) for p in products if isinstance(p.get('external_sell_price'), (int, float)) and p.get('external_sell_price') > 0]
        total_variants = sum(p.get('variants_count', len(p.get('variants', []))) for p in products)
        products_with_variants = sum(1 for p in products if p.get('variants_count', len(p.get('variants', []))) > 0)
        total_images = sum(p.get('images_count', len(p.get('images', []))) for p in products)
        brands = {p.get('brand') for p in products if p.get('brand')}
        
        logger.info(f"Total products: {len(products)}")
        logger.info(f"Unique brands: {len(brands)}")
        if prices:
            logger.info(f"Price (Min/Max/Avg): ${min(prices):.2f} / ${max(prices):.2f} / ${sum(prices)/len(prices):.2f}")
        logger.info(f"Total variants: {total_variants} | Products with variants: {products_with_variants}")
        logger.info(f"Total images: {total_images}")
        logger.info("------------------------------------")
    
    def print_statistics(self, general_products: List[Dict], detailed_products: List[Dict]):
        logger.info("\n" + "="*50)
        logger.info("SCRAPING STATISTICS")
        logger.info("="*50)
        logger.info(f"General products: {len(general_products)}")
        logger.info(f"Detailed products: {len(detailed_products)}")
        
        if detailed_products:
            # Calculate price statistics
            prices = []
            total_variants = 0
            products_with_variants = 0
            total_images = 0
            
            for product in detailed_products:
                # Price statistics
                price = product.get('external_sell_price', 0)
                if isinstance(price, (int, float)) and price > 0:
                    prices.append(float(price))
                
                # Variant statistics
                variants = product.get('variants', [])
                if isinstance(variants, list):
                    variant_count = len(variants)
                    total_variants += variant_count
                    if variant_count > 0:
                        products_with_variants += 1
                else:
                    # Handle variants_count field if variants is JSON string
                    variant_count = product.get('variants_count', 0)
                    total_variants += variant_count
                    if variant_count > 0:
                        products_with_variants += 1
                
                # Image statistics  
                images = product.get('images', [])
                if isinstance(images, list):
                    total_images += len(images)
                else:
                    total_images += product.get('images_count', 0)
            
            # Print price statistics
            if prices:
                logger.info(f"\nPrice Statistics:")
                logger.info(f"  - Minimum price: ${min(prices):.2f}")
                logger.info(f"  - Maximum price: ${max(prices):.2f}")
                logger.info(f"  - Average price: ${sum(prices)/len(prices):.2f}")
                logger.info(f"  - Products with price: {len(prices)}")
            
            # Print variant statistics
            logger.info(f"\nVariant Statistics:")
            logger.info(f"  - Total variants: {total_variants}")
            logger.info(f"  - Products with variants: {products_with_variants}")
            if len(detailed_products) > 0:
                logger.info(f"  - Average variants per product: {total_variants/len(detailed_products):.1f}")
            
            # Print image statistics
            logger.info(f"\nImage Statistics:")
            logger.info(f"  - Total images: {total_images}")
            if len(detailed_products) > 0:
                logger.info(f"  - Average images per product: {total_images/len(detailed_products):.1f}")
        
        logger.info("="*50) 