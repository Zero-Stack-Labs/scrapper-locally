"""Stock scraper for variant stock information with rate limiting."""

import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_scraper import BaseScraper
from utils.rate_limiter import RateLimiter
from models.variant import Variant


class StockScraper(BaseScraper):
    """Scraper for stock information with advanced rate limiting."""
    
    def __init__(self, calls_per_second: float = 2.0, max_retries: int = 3):
        """
        Initialize stock scraper with rate limiting.
        
        Args:
            calls_per_second: Maximum API calls per second
            max_retries: Maximum number of retries for failed requests
        """
        super().__init__()
        self.rate_limiter = RateLimiter(calls_per_second, max_retries)
    
    def get_variant_stock_info(self, product_id: str, upc: str) -> Dict:
        """
        Get stock information for a variant with rate limiting.
        
        Args:
            product_id: Product ID from the main product
            upc: UPC code of the variant
            
        Returns:
            Dictionary with stock information or empty dict if failed
        """
        if not product_id or not upc:
            return {}
        
        url = f"https://www.locally.com/product_stock/{product_id}?store={self.store_id}&sort=pop&upc={upc}&store={self.store_id}"
        headers = self.get_stock_headers(product_id)
        
        def make_stock_request():
            return self.make_request(url, headers)
        
        # Use rate limiter to execute the request
        response = self.rate_limiter.execute_with_retry(make_stock_request)
        
        if response is None:
            return {}
        
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                print(f"Error parsing stock JSON for UPC {upc}: {e}")
                return {}
        elif response.status_code == 429:
            print(f"Rate limited for UPC {upc}")
            return {}
        else:
            print(f"Stock API error {response.status_code} for UPC {upc}")
            return {}
    
    def update_variants_with_stock(self, variants: List[Dict], product_id: str, 
                                  max_workers: int = 3) -> List[Dict]:
        """
        Update variants with stock information using controlled concurrency.
        
        Args:
            variants: List of variant dictionaries
            product_id: Product ID for stock API calls
            max_workers: Maximum concurrent workers (keep low to avoid rate limiting)
            
        Returns:
            List of updated variant dictionaries with stock information
        """
        if not variants:
            return variants
        
        print(f"Updating stock for {len(variants)} variants (max {max_workers} workers)...")
        
        updated_variants = []
        
        # Filter variants that have UPC for stock checking
        variants_with_upc = [v for v in variants if v.get('upc')]
        variants_without_upc = [v for v in variants if not v.get('upc')]
        
        print(f"  - {len(variants_with_upc)} variants with UPC (will check stock)")
        print(f"  - {len(variants_without_upc)} variants without UPC (skipping stock)")
        
        # Process variants with UPC using controlled concurrency
        if variants_with_upc:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_variant = {
                    executor.submit(self._update_single_variant_stock, variant, product_id): variant
                    for variant in variants_with_upc
                }
                
                for future in as_completed(future_to_variant):
                    variant = future_to_variant[future]
                    try:
                        updated_variant = future.result()
                        updated_variants.append(updated_variant)
                    except Exception as exc:
                        print(f'Error updating stock for variant {variant.get("name", "Unknown")}: {exc}')
                        # Add variant without stock update
                        updated_variants.append(variant)
        
        # Add variants without UPC (no stock check)
        for variant in variants_without_upc:
            variant['stock_status'] = 'No UPC Available'
            variant['external_quantity'] = None
            variant['store_name'] = ''
            variant['store_address'] = ''
            variant['store_id'] = ''
            variant['variant_price'] = ''
            variant['variant_currency'] = ''
            variant['stock_data'] = {}
            updated_variants.append(variant)
        
        print(f"Stock update completed for {len(updated_variants)} variants")
        return updated_variants
    
    def _update_single_variant_stock(self, variant: Dict, product_id: str) -> Dict:
        """
        Update a single variant with stock information.
        
        Args:
            variant: Variant dictionary
            product_id: Product ID for stock API call
            
        Returns:
            Updated variant dictionary
        """
        upc = variant.get('upc', '')
        if not upc:
            return variant
        
        # Get stock information
        stock_data = self.get_variant_stock_info(product_id, upc)
        
        # Create Variant object to handle stock update
        variant_obj = Variant(variant.get('name', ''), upc, variant.get('page_id_variant', ''))
        variant_obj.update_stock_info(stock_data)
        
        # Update the original variant dict with stock info
        variant.update({
            'stock_status': variant_obj.stock_status,
            'external_quantity': variant_obj.external_quantity,
            'store_name': variant_obj.store_name,
            'store_address': variant_obj.store_address,
            'store_id': variant_obj.store_id,
            'variant_price': variant_obj.variant_price,
            'variant_currency': variant_obj.variant_currency,
            'stock_data': variant_obj.stock_data
        })
        
        return variant
    
    def process_products_with_stock(self, products: List[Dict], max_workers: int = 3) -> List[Dict]:
        """
        Process multiple products and update all their variants with stock information.
        
        Args:
            products: List of product dictionaries
            max_workers: Maximum concurrent workers for stock calls
            
        Returns:
            List of products with updated variant stock information
        """
        if not products:
            return products
        
        print(f"Processing {len(products)} products for stock information...")
        
        updated_products = []
        
        for i, product in enumerate(products, 1):
            print(f"Processing product {i}/{len(products)}: {product.get('name', 'Unknown')}")
            
            variants = product.get('variants', [])
            if variants:
                # Update variants with stock information
                updated_variants = self.update_variants_with_stock(
                    variants, 
                    product.get('external_id', ''),
                    max_workers
                )
                product['variants'] = updated_variants
            
            updated_products.append(product)
            
            # Add a small delay between products to be extra safe
            if i < len(products):
                time.sleep(1)
        
        print(f"Stock processing completed for {len(updated_products)} products")
        return updated_products 