"""Data export utilities for saving scraped data."""

import json
import pandas as pd
from typing import List, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DataExporter:
    """Handles data export to various formats."""
    
    def __init__(self, output_dir: str = ".", filename_suffix: str = ""):
        """
        Initialize data exporter.
        
        Args:
            output_dir: Directory to save files in
            filename_suffix: Suffix to add to filenames (e.g., "85940_123")
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.filename_suffix = filename_suffix
    
    def save_products_json(self, products: List[Dict], filename: str = "products.json"):
        """
        Save products to JSON file.
        
        Args:
            products: List of product dictionaries
            filename: Output filename
        """
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(products)} products to {filepath}")
    
    def save_products_csv(self, products: List[Dict], filename: str = "products.csv"):
        """
        Save products to CSV file with optimized structure.
        
        Args:
            products: List of product dictionaries
            filename: Output filename
        """
        if not products:
            logger.warning(f"No products to save to {filename}")
            return
        
        filepath = self.output_dir / filename
        
        # Convert to DataFrame
        df = pd.DataFrame(products)
        
        # Save to CSV
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Saved {len(products)} products to {filepath}")
    
    def save_unified_products(self, products: List[Dict]):
        """Save unified products (general + detailed data combined)."""
        if not products:
            return
        
        logger.info(f"Saving {len(products)} unified products...")
        
        # Generate filenames with suffix
        json_filename = f"products_{self.filename_suffix}.json" if self.filename_suffix else "products.json"
        csv_filename = f"products_{self.filename_suffix}.csv" if self.filename_suffix else "products.csv"
        
        # Save JSON with full structure
        self.save_products_json(products, json_filename)
        
        # Prepare CSV-optimized data
        csv_products = [self._convert_for_csv(p) for p in products]
        
        # Save CSV
        self.save_products_csv(csv_products, csv_filename)
        
        logger.info("Unified products saved successfully")
    
    def save_general_products(self, products: List[Dict]):
        """Save general product summaries (from listing pages)."""
        if not products:
            return
        
        logger.info(f"Saving {len(products)} general products...")
        
        # Save JSON
        self.save_products_json(products, "products_general.json")
        
        # Save CSV  
        self.save_products_csv(products, "products_general.csv")
        
        logger.info("General products saved successfully")
    
    def save_detailed_products(self, products: List[Dict]):
        """Save detailed products with variants as JSON in product."""
        if not products:
            return
        
        logger.info(f"Saving {len(products)} detailed products...")
        
        # Save complete JSON structure
        self.save_products_json(products, "products_details.json")
        
        # Prepare CSV-optimized data
        csv_products = []
        for product in products:
            # Use the to_dict_for_csv method if available, otherwise convert manually
            if hasattr(product, 'to_dict_for_csv'):
                csv_product = product.to_dict_for_csv()
            else:
                csv_product = self._convert_for_csv(product)
            csv_products.append(csv_product)
        
        # Save CSV
        self.save_products_csv(csv_products, "products_details.csv")
        
        logger.info("Detailed products saved successfully")
    
    def _convert_for_csv(self, product: Dict) -> Dict:
        """Convert product dictionary for CSV export."""
        csv_product = product.copy()
        
        # Convert images list to pipe-separated string
        if 'images' in csv_product and isinstance(csv_product['images'], list):
            csv_product['images_csv'] = '|'.join(csv_product['images'])
            del csv_product['images']
        
        # Convert variants list to JSON string for CSV
        if 'variants' in csv_product and isinstance(csv_product['variants'], list):
            csv_product['variants_json'] = json.dumps(csv_product['variants'], ensure_ascii=False)
            del csv_product['variants']
        
        return csv_product
    
    def print_unified_statistics(self, products: List[Dict]):
        """Print statistics for unified products."""
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
        """Print statistics of scraped products."""
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