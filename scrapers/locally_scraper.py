"""Main locally scraper that orchestrates all scraping components."""

import time
from typing import List, Tuple, Dict
from urllib.parse import urljoin

from .page_scraper import PageScraper
from .product_scraper import ProductScraper
from utils.data_export import DataExporter
from models.product import Product


class LocallyScraper:
    """Main scraper that orchestrates all scraping operations."""
    
    def __init__(self, enable_stock_scraping: bool = True, output_dir: str = ".", store_config: dict = None, filename_suffix: str = ""):
        """
        Initialize the main scraper.
        
        Args:
            enable_stock_scraping: Whether to scrape stock information for variants (deprecated - now always extracted from product page)
            output_dir: Directory to save output files
            store_config: Dictionary with store configuration (store_id, lat, lng, zipcode)
            filename_suffix: Suffix for output filenames (e.g., "85940_123")
        """
        self.store_config = store_config or {'store_id': '85940', 'lat': 30.838215, 'lng': -87.20102, 'zipcode': '123'}
        
        self.page_scraper = PageScraper()
        self.product_scraper = ProductScraper()
        self.data_exporter = DataExporter(output_dir, filename_suffix=filename_suffix)
        
        # Configure scrapers with store information
        self.page_scraper.update_store_id(self.store_config['store_id'])
        self.product_scraper.update_store_id(self.store_config['store_id'])
        
        # Note: enable_stock_scraping is now deprecated since we extract everything from product pages
        self.enable_stock_scraping = True  # Always True since we get it from product page HTML
    
    def initialize(self) -> bool:
        """Initialize the scraping session."""
        print(f"Initializing location for store {self.store_config['store_id']} at coordinates ({self.store_config['lat']}, {self.store_config['lng']})...")
        return self.page_scraper.initialize_location(
            lat=self.store_config['lat'], 
            lng=self.store_config['lng']
        )
    
    def update_configuration(self, store_id: str = None, calls_per_second: float = None, enable_stock_scraping: bool = None):
        """
        Update scraper configuration.
        
        Args:
            store_id: Store ID to scrape from
            calls_per_second: Deprecated - no longer needed since we don't use stock API
            enable_stock_scraping: Deprecated - stock info always extracted from product pages
        """
        if store_id:
            self.page_scraper.store_id = store_id
            self.product_scraper.store_id = store_id
        
        # Note: calls_per_second and enable_stock_scraping are deprecated
        # since we no longer make separate stock API calls
    
    def get_status(self) -> dict:
        """Get current scraper status and configuration."""
        return {
            'store_id': self.store_config['store_id'],
            'zipcode': self.store_config['zipcode'],
            'lat': self.store_config['lat'],
            'lng': self.store_config['lng'],
            'stock_scraping_enabled': True,  # Always True since we extract from HTML
            'rate_limit': None,  # No longer applicable
            'output_directory': self.data_exporter.output_dir
        }
    
    def scrape_all_products_with_delays(self, 
                                       start_page: int = 0,
                                       page_delay: float = 5.0,
                                       max_product_workers: int = 5,
                                       max_stock_workers: int = 3,  # Deprecated parameter
                                       save_progress_every: int = 5) -> List[dict]:
        """
        Main scraping function that processes all pages with delays.
        
        Args:
            start_page: Starting page number
            page_delay: Delay in seconds between pages
            max_product_workers: Maximum workers for product detail scraping
            max_stock_workers: Deprecated - no longer used since stock comes from product pages
            save_progress_every: Save progress every N pages
            
        Returns:
            List of unified product dictionaries with all information
        """
        all_products = []
        page = start_page
        seen_product_ids = set()
        
        if not self.initialize():
            print("Failed to initialize. Aborting scraping.")
            return []
        
        print("Starting page-by-page scraping with delays...")
        print("Note: Extracting unified product data with stock info from product pages!")
        
        while True:
            print(f"\n{'='*60}")
            print(f"PROCESSING PAGE {page}")
            print(f"{'='*60}")
            
            # Scrape products from the listing page (basic info)
            general_products = self.page_scraper.scrape_page(page)
            
            if not general_products:
                print(f"No products found on page {page}. Ending scraping.")
                break
            
            # Filter new products
            new_products = [p for p in general_products if p.external_id not in seen_product_ids]
            
            if not new_products:
                print(f"All products on page {page} have already been processed. Ending scraping.")
                break
            
            print(f"New products to process: {len(new_products)}")
            
            # Track seen IDs
            for product in new_products:
                seen_product_ids.add(product.external_id)
            
            # Get detailed information and merge with general data
            unified_products = self._get_unified_product_data(new_products, max_product_workers, page)
            
            # Add to main list
            all_products.extend(unified_products)
            
            print(f"Page {page} completed: {len(unified_products)} unified products obtained")
            
            # Save progress periodically
            if page % save_progress_every == 0:
                print(f"Saving progress up to page {page}...")
                self.save_results(all_products)
            
            # Wait before processing next page
            if page_delay > 0:
                print(f"Waiting {page_delay} seconds before processing page {page + 1}...")
                time.sleep(page_delay)
            
            page += 1
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETED")
        print(f"{'='*60}")
        print(f"Total pages processed: {page-1}")
        print(f"Total unified products: {len(all_products)}")
        
        return all_products
    
    def scrape_specific_pages(self, pages: List[int], **kwargs) -> List[dict]:
        """
        Scrape specific pages only.
        
        Args:
            pages: List of page numbers to scrape
            **kwargs: Additional arguments passed to scraping methods
            
        Returns:
            List of unified product dictionaries
        """
        all_products = []
        
        if not self.initialize():
            print("Failed to initialize. Aborting scraping.")
            return []
        
        for page in pages:
            print(f"Scraping page {page}...")
            
            # Get general products from listing
            general_products = self.page_scraper.scrape_page(page)
            if not general_products:
                continue
            
            # Get unified data
            unified_products = self._get_unified_product_data(
                general_products, 
                kwargs.get('max_product_workers', 5), 
                page
            )
            
            all_products.extend(unified_products)
        
        return all_products
    
    def _get_unified_product_data(self, general_products: List[Product], max_workers: int, page: int) -> List[dict]:
        """
        Combine general product data with detailed product data into unified records.
        
        Args:
            general_products: List of general Product objects from listing page
            max_workers: Maximum workers for detail scraping
            page: Current page number
            
        Returns:
            List of unified product dictionaries
        """
        unified_products = []
        
        # Get product URLs for detail scraping
        product_urls = [urljoin(self.page_scraper.base_url, p.url) for p in general_products if p.url]
        
        if product_urls:
            # Initialize location before scraping product details
            self.product_scraper.initialize_location(
                lat=self.store_config['lat'], 
                lng=self.store_config['lng']
            )
            
            # Get detailed information
            detailed_products = self.product_scraper.get_product_details_batch(
                product_urls, max_workers
            )
            
            # Create a lookup dict for detailed products
            detailed_lookup = {p.external_id: p for p in detailed_products}
            
            # Merge general and detailed data
            for general_product in general_products:
                # Start with general product data
                unified_data = general_product.to_dict()
                unified_data['page_number'] = page
                
                # Add store configuration data
                unified_data['store_id'] = self.store_config['store_id']
                unified_data['lat'] = self.store_config['lat']
                unified_data['lng'] = self.store_config['lng']
                unified_data['zipcode'] = self.store_config['zipcode']
                unified_data['store_name'] = self.store_config['store_name']
                
                # Find corresponding detailed product
                detailed_product = detailed_lookup.get(general_product.external_id)
                
                if detailed_product:
                    # Merge detailed data (prioritizing detailed over general for conflicts)
                    detailed_data = detailed_product.to_dict()
                    
                    # Get the product's main SKU from the general data (listing page)
                    product_sku = unified_data.get('sku')
                    
                    # Ensure all variants inherit the main product SKU, which comes from the listing page
                    if product_sku and 'variants' in detailed_data:
                        for i in range(len(detailed_data['variants'])):
                            detailed_data['variants'][i]['sku'] = product_sku
                    
                    # Merge fields, keeping general data for fields that detailed doesn't have
                    # and detailed data for fields it does have
                    unified_data.update({
                        # Keep general data for these fields (usually better from listing)
                        'url': unified_data.get('url', detailed_data.get('url', '')),
                        'sku': product_sku,  # Always use the SKU from the listing page
                        'currency': unified_data.get('currency', 'USD'),
                        
                        # Use detailed data for these fields (better from product page)
                        'description': detailed_data.get('description', unified_data.get('description', '')),
                        'images': detailed_data.get('images', []),
                        'images_count': len(detailed_data.get('images', [])),
                        'variants': detailed_data.get('variants', []),
                        'variants_count': len(detailed_data.get('variants', [])),
                        
                        # Price - prefer detailed if available
                        'external_sell_price': detailed_data.get('external_sell_price', unified_data.get('external_sell_price', 0.0)),
                    })
                    
                    print(f"✓ Merged data for {general_product.name} (variants: {len(detailed_data.get('variants', []))})")
                else:
                    print(f"⚠ No detailed data for {general_product.name}")
                    # Add default values for missing detailed fields
                    unified_data.update({
                        'description': '',
                        'variants': [],
                        'variants_count': 0,
                        'images_count': len(unified_data.get('images', [])),
                        'currency': unified_data.get('currency', 'USD')
                    })
                    # Store configuration is already added above
                
                unified_products.append(unified_data)
        else:
            # Handle case where there are no product URLs
            for general_product in general_products:
                unified_data = general_product.to_dict()
                unified_data['page_number'] = page
                
                # Add store configuration data
                unified_data['store_id'] = self.store_config['store_id']
                unified_data['lat'] = self.store_config['lat']
                unified_data['lng'] = self.store_config['lng']
                unified_data['zipcode'] = self.store_config['zipcode']
                unified_data['store_name'] = self.store_config['store_name']
                
                # Add default values for missing detailed fields
                unified_data.update({
                    'description': '',
                    'variants': [],
                    'variants_count': 0,
                    'images_count': len(unified_data.get('images', [])),
                    'currency': unified_data.get('currency', 'USD')
                })
                
                unified_products.append(unified_data)
        
        return unified_products
    
    def save_results(self, products: List[dict]):
        """
        Save unified scraping results to files.
        
        Args:
            products: List of unified product dictionaries
        """
        # Save unified products
        self.data_exporter.save_unified_products(products)
        
        # Print statistics
        self.data_exporter.print_unified_statistics(products)
        
        print(f"\nScraping completed successfully!")
        print(f"Generated files:")
        print(f"  - products.csv ({len(products)} products)")
        print(f"  - products.json")
        print(f"\nNote: All product data unified with variant stock information!") 