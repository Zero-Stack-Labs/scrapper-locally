import time
import json
from typing import List, Dict
from urllib.parse import urljoin
from .page_scraper import PageScraper
from .product_scraper import ProductScraper
from models.product import Product
from models.variant import Variant
from pathlib import Path
from utils.logging_config import get_logger

logger = get_logger(__name__)

class LocallyScraper:
    
    def __init__(self, output_dir: str = ".", store_config: dict = None):
        self.store_config = store_config or {'store_id': '85940', 'lat': 30.838215, 'lng': -87.20102, 'zipcode': '123'}
        self.output_dir = output_dir
        
        self.page_scraper = PageScraper()
        self.product_scraper = ProductScraper()
        
        self.page_scraper.update_store_id(self.store_config['store_id'])
        self.product_scraper.update_store_id(self.store_config['store_id'])
    
    def initialize(self) -> bool:
        logger.debug(f"Initializing location for store {self.store_config['store_id']}...")
        return self.page_scraper.initialize_location(
            lat=self.store_config['lat'], 
            lng=self.store_config['lng']
        )
    
    def update_configuration(self, store_id: str = None):
        if store_id:
            self.page_scraper.store_id = store_id
            self.product_scraper.store_id = store_id
    
    def scrape_all_products_with_delays(self, 
                                       page_delay: float = 5.0,
                                       max_product_workers: int = 5,
                                       max_page_workers: int = 3,
                                       save_progress_every: int = 5,
                                       start_page: int = 0,
                                       max_pages: int = None) -> List[dict]:
        if not self.initialize():
            logger.error("Failed to initialize. Aborting scraping.")
            return []
        
        if max_page_workers > 1:
            logger.info(f"Starting PARALLEL page scraping with {max_page_workers} workers...")
            return self._scrape_pages_parallel(
                page_delay, max_product_workers, max_page_workers, 
                save_progress_every, start_page, max_pages
            )
        else:
            logger.info("Starting SEQUENTIAL page scraping...")
            return self._scrape_pages_sequential(
                page_delay, max_product_workers, 
                save_progress_every, start_page, max_pages
            )
    
    def _get_detailed_products(self, general_products: List[Product], page: int, max_workers: int = 5) -> List[dict]:
        unified_products = []
        
        # Debug: Log general products URLs
        logger.info(f"Processing {len(general_products)} general products from page {page}")
        
        product_urls = [urljoin(self.page_scraper.base_url, p.url) for p in general_products if p.url]
        
        logger.info(f"Generated {len(product_urls)} product URLs for detailed scraping")
        
        if product_urls:
            self.product_scraper.initialize_location(
                lat=self.store_config['lat'], 
                lng=self.store_config['lng']
            )
            
            detailed_products = self.product_scraper.get_product_details_batch(
                product_urls, 
                max_workers=max_workers
            )
            
            logger.info(f"Retrieved {len(detailed_products)} detailed products")
            
            detailed_products_dict = {p.external_id: p for p in detailed_products}
            
            for general_product in general_products:
                if general_product.external_id in detailed_products_dict:
                    detailed_product = detailed_products_dict[general_product.external_id]
                    
                    merged_product = self._merge_product_data(general_product, detailed_product)
                    merged_product['page_number'] = page
                    
                    if not merged_product['variants']:
                        logger.warning(f"  ⚠️ Product {merged_product['external_id']}: No variants found")
                    
                    unified_products.append(merged_product)
                else:
                    logger.warning(f"  ❌ Product {general_product.external_id}: Not found in detailed results, using general data only")
                    general_dict = general_product.to_dict()
                    general_dict['page_number'] = page
                    unified_products.append(general_dict)
        else:
            logger.warning("No product URLs found - using general product data only")
            for general_product in general_products:
                general_dict = general_product.to_dict()
                general_dict['page_number'] = page
                unified_products.append(general_dict)
        
        return unified_products
    
    def _merge_product_data(self, general_product: Product, detailed_product: Product) -> dict:
        merged_data = detailed_product.to_dict()
        
        if not merged_data.get('name') and general_product.name:
            merged_data['name'] = general_product.name
        
        if not merged_data.get('brand') and general_product.brand:
            merged_data['brand'] = general_product.brand
        
        if not merged_data.get('url') and general_product.url:
            merged_data['url'] = general_product.url
        
        if not merged_data.get('external_sell_price') and general_product.external_sell_price:
            merged_data['external_sell_price'] = general_product.external_sell_price
        
        if not merged_data.get('sku') and general_product.sku:
            merged_data['sku'] = general_product.sku
        
        if not merged_data.get('condition') and general_product.condition:
            merged_data['condition'] = general_product.condition
        
        if not merged_data.get('currency') and general_product.currency:
            merged_data['currency'] = general_product.currency
        
        if not merged_data.get('images') and general_product.images:
            merged_data['images'] = general_product.images
        
        final_sku = merged_data.get('sku', '')
        if final_sku and merged_data.get('variants'):
            for variant in merged_data['variants']:
                if isinstance(variant, dict):
                    variant['sku'] = final_sku
        
        # Asignar imagen del producto a variantes que no tengan imagen
        product_images = merged_data.get('images', [])
        main_image = product_images[0] if product_images else ''
        
        if main_image and merged_data.get('variants'):
            for variant in merged_data['variants']:
                if isinstance(variant, dict) and not variant.get('image'):
                    variant['image'] = main_image
        
        merged_data['store_id'] = self.store_config.get('store_id', '')
        merged_data['lat'] = self.store_config.get('lat', 0.0)
        merged_data['lng'] = self.store_config.get('lng', 0.0)
        merged_data['zipcode'] = self.store_config.get('zipcode', '')
        merged_data['store_name'] = self.store_config.get('store_name', '')
        
        return merged_data

    def log_results(self, products: List[dict]):
        if not products:
            return

        products_with_variants = sum(1 for p in products if p.get('variants'))
        total_variants = sum(len(p.get('variants', [])) for p in products)

        summary = (
            f"Total products: {len(products)}, "
            f"Products with variants: {products_with_variants}, "
            f"Total variants: {total_variants}"
        )

        if products_with_variants > 0:
            avg_variants = total_variants / products_with_variants
            summary += f", Average variants: {avg_variants:.2f}"

        logger.info(summary)

    def _scrape_pages_sequential(self, page_delay: float, max_product_workers: int, 
                                save_progress_every: int, start_page: int, max_pages: int) -> List[dict]:
        all_products = []
        page = start_page
        seen_product_ids = set()
        
        while True:
            if max_pages is not None and (page - start_page) >= max_pages:
                logger.info(f"Reached maximum pages limit ({max_pages}). Ending scraping.")
                break
                
            logger.info(f"--- Processing page {page} ---")
            
            general_products = self.page_scraper.scrape_page(page)
            
            if not general_products:
                logger.info(f"No products found on page {page}. Ending scraping.")
                break
            
            new_products = [p for p in general_products if p.external_id not in seen_product_ids]
            
            if not new_products:
                logger.info(f"All products on page {page} have already been processed. Ending scraping.")
                break
            
            logger.info(f"New products to process: {len(new_products)}")
            
            for product in new_products:
                seen_product_ids.add(product.external_id)
            
            unified_products = self._get_detailed_products(new_products, page, max_product_workers)
            
            all_products.extend(unified_products)
            
            logger.info(f"Page {page} completed: {len(unified_products)} unified products obtained")

            if page % save_progress_every == 0:
                logger.info(f"Saving progress up to page {page}...")
                self.log_results(all_products)
            
            if page_delay > 0:
                logger.info(f"Waiting {page_delay} seconds before processing page {page + 1}...")
                time.sleep(page_delay)
            
            page += 1
        
        logger.info("--- SEQUENTIAL SCRAPING COMPLETED ---")
        logger.info(f"Total pages processed: {page-1 if page > 0 else 0}")
        logger.info(f"Total unified products: {len(all_products)}")
        
        return all_products

    def _scrape_pages_parallel(self, page_delay: float, max_product_workers: int, max_page_workers: int,
                              save_progress_every: int, start_page: int, max_pages: int) -> List[dict]:
        import concurrent.futures
        import threading
        
        all_products = []
        seen_product_ids = set()
        page_lock = threading.Lock()
        
        max_pages_to_process = max_pages if max_pages is not None else 50
        
        pages_to_scrape = list(range(start_page, start_page + max_pages_to_process))
        
        logger.info(f"Processing {len(pages_to_scrape)} pages in parallel with {max_page_workers} workers...")
        
        def process_single_page(page_num):
            try:
                page_scraper = PageScraper()
                page_scraper.update_store_id(self.store_config['store_id'])
                page_scraper.initialize_location(
                    lat=self.store_config['lat'], 
                    lng=self.store_config['lng']
                )
                
                logger.info(f"--- Processing page {page_num} ---")
                general_products = page_scraper.scrape_page(page_num)
                
                if not general_products:
                    logger.info(f"No products found on page {page_num}")
                    return []
                
                with page_lock:
                    new_products = [p for p in general_products if p.external_id not in seen_product_ids]
                    for product in new_products:
                        seen_product_ids.add(product.external_id)
                
                if not new_products:
                    logger.info(f"No new products on page {page_num}")
                    return []
                
                logger.info(f"Page {page_num}: {len(new_products)} new products")
                
                unified_products = self._get_detailed_products(new_products, page_num, max_product_workers)
                
                logger.info(f"Page {page_num} completed: {len(unified_products)} unified products")
                
                if page_delay > 0:
                    time.sleep(page_delay)
                
                return unified_products
                
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {e}")
                return []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_page_workers) as executor:
            future_to_page = {
                executor.submit(process_single_page, page): page 
                for page in pages_to_scrape
            }
            
            for future in concurrent.futures.as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    page_products = future.result()
                    all_products.extend(page_products)
                    
                    if len(all_products) % (save_progress_every * 10) == 0:
                        logger.info(f"Progress: {len(all_products)} total products collected so far...")
                        
                except Exception as e:
                    logger.error(f"Page {page_num} generated an exception: {e}")
        
        logger.info("--- PARALLEL SCRAPING COMPLETED ---")
        logger.info(f"Total pages processed: {len(pages_to_scrape)}")
        logger.info(f"Total unified products: {len(all_products)}")
        
        return all_products