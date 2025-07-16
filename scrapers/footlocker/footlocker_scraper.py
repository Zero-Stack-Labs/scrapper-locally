import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import time

from scrapers.base_scraper import BaseScraper
from models.product import Product
from .footlocker_api_scraper import FootlockerApiScraper
from .footlocker_product_scraper import FootlockerProductScraper
from .footlocker_mapper import FootlockerMapper
from utils.logging_config import get_logger


class FootlockerScraper(BaseScraper):
    def __init__(self, base_url: str = "https://www.footlocker.com", x_kpsdk_ct: str = '', store_id: str = '', latitude: float = 0.0, longitude: float = 0.0, zipcode: str = ''):
        super().__init__()
        self.logger = get_logger(__name__)
        
        self.store_id = store_id
        self.latitude = latitude
        self.longitude = longitude
        self.zipcode = zipcode
        
        self.api_scraper = FootlockerApiScraper(
            base_url=base_url, 
            x_kpsdk_ct=x_kpsdk_ct,
            store_id=self.store_id
        )
        self.product_scraper = FootlockerProductScraper(base_url=base_url, x_kpsdk_ct=x_kpsdk_ct)
        
    def scrape_products(
        self, 
        query: str, 
        max_pages: int = 2,
        max_detail_workers: int = 3,
        detail_delay: float = 1.0,
        api_delay: float = 2.0
    ) -> List[Product]:
        try:
            basic_products = self.api_scraper.scrape_all_products(
                query, max_pages=max_pages, delay=api_delay,
                latitude=self.latitude, longitude=self.longitude, zipcode=self.zipcode
            )
            
            if not basic_products:
                return []
            
            product_ids = [product.external_id for product in basic_products]
            
            detailed_products_data = self.product_scraper.get_product_details_batch(
                product_ids, 
                max_workers=max_detail_workers, 
                delay=detail_delay
            )
            
            return self._merge_product_data(basic_products, detailed_products_data)
            
        except Exception as e:
            self.logger.error(f"Error en scraping de Footlocker: {e}")
            return []
    
    def _merge_product_data(self, basic_products: List[Product], detailed_products_data: List[Dict]) -> List[Product]:
        detailed_dict = {data['product_id']: data for data in detailed_products_data if data}
        
        merged_products = []
        for basic_product in basic_products:
            detailed_data = detailed_dict.get(basic_product.external_id)
            
            if detailed_data:
                if detailed_data.get('description') and not basic_product.description:
                    basic_product.description = detailed_data['description']
                
                if detailed_data.get('meta_description'):
                    if basic_product.description:
                        basic_product.description += f" | {detailed_data['meta_description']}"
                    else:
                        basic_product.description = detailed_data['meta_description']
                
                if detailed_data.get('brand') and not basic_product.brand:
                    basic_product.brand = detailed_data['brand']
                
                if detailed_data.get('sku') and not basic_product.sku:
                    basic_product.sku = detailed_data['sku']
                
                if detailed_data.get('image_url') and not basic_product.images:
                    basic_product.images = [detailed_data['image_url']]
                elif detailed_data.get('image_url') and detailed_data['image_url'] not in basic_product.images:
                    basic_product.images.append(detailed_data['image_url'])
                
                if detailed_data.get('condition') and basic_product.condition in ['unknown', '', None]:
                    basic_product.condition = detailed_data['condition']
                
                if detailed_data.get('variants'):
                    basic_product.variants = detailed_data['variants']
                    
                    # Determinar stock_status del producto basándose en las variantes
                    has_in_stock = any(
                        variant.get('stock_status') == 'in_stock' 
                        for variant in detailed_data['variants']
                    )
                    basic_product.stock_status = "in_stock" if has_in_stock else "out_of_stock"
                    
                    self.logger.debug(f"✅ Merged {len(detailed_data['variants'])} variants for product {basic_product.external_id}")
                else:
                    self.logger.debug(f"⚠️ No variants found in detailed data for product {basic_product.external_id}")
                    basic_product.stock_status = "out_of_stock"
                
            merged_products.append(basic_product)
            
        return merged_products
    
    def close(self):
        if self.api_scraper:
            self.api_scraper.close()
        if self.product_scraper:
            self.product_scraper.close() 