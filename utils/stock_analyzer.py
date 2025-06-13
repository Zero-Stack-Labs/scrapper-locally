"""Stock analyzer for multi-location product availability."""

import json
import csv
from typing import List, Dict, Set
from collections import defaultdict
from pathlib import Path


class StockAnalyzer:
    """Analyze product stock availability across multiple locations."""
    
    def __init__(self, output_dir: str = "."):
        """Initialize the stock analyzer."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_stock_analysis_files(self, all_products: List[Dict], store_configurations: List[Dict]):
        """
        Generate products_in_stock and products_out_stock files based on availability across all locations.
        
        Args:
            all_products: List of all products from all locations
            store_configurations: List of store configuration dictionaries
        """
        print(f"\n📊 ANALYZING STOCK ACROSS {len(store_configurations)} LOCATIONS")
        print("="*60)
        
        # Get all zipcodes from configurations
        all_zipcodes = {config['zipcode'] for config in store_configurations}
        print(f"Analyzing availability for zipcodes: {sorted(all_zipcodes)}")
        
        # Group products by external_id and analyze availability
        product_availability = self._analyze_product_availability(all_products, all_zipcodes)
        
        # Separate products into in_stock and out_stock
        products_in_stock, products_out_stock = self._categorize_products(product_availability, all_zipcodes)
        
        # Generate files
        self._save_stock_files(products_in_stock, products_out_stock)
        
        # Print statistics
        self._print_stock_statistics(products_in_stock, products_out_stock, all_zipcodes)
    
    def _analyze_product_availability(self, all_products: List[Dict], all_zipcodes: Set[str]) -> Dict:
        """
        Analyze product availability across all locations.
        
        Returns:
            Dict mapping external_id to availability information
        """
        product_availability = defaultdict(lambda: {
            'locations': {},  # zipcode -> product_data
            'available_zipcodes': set(),
            'in_stock_zipcodes': set(),
            'product_info': None
        })
        
        for product in all_products:
            external_id = product.get('external_id')
            zipcode = product.get('location_zipcode')
            
            if not external_id or not zipcode:
                continue
            
            # Store product data for this location
            product_availability[external_id]['locations'][zipcode] = product
            product_availability[external_id]['available_zipcodes'].add(zipcode)
            
            # Store general product info (use first occurrence)
            if not product_availability[external_id]['product_info']:
                product_availability[external_id]['product_info'] = product
            
            # Check if product has in-stock variants in this location
            if self._has_in_stock_variants(product):
                product_availability[external_id]['in_stock_zipcodes'].add(zipcode)
        
        return dict(product_availability)
    
    def _has_in_stock_variants(self, product: Dict) -> bool:
        """Check if a product has any in-stock variants."""
        variants = product.get('variants', [])
        
        if not variants:
            # If no variants, check general stock status or assume available if price exists
            return product.get('external_sell_price', 0) > 0
        
        # Check if any variant is in stock
        for variant in variants:
            stock_status = variant.get('stock_status', '').lower()
            if stock_status in ['in stock', 'available', 'in_stock']:
                return True
        
        return False
    
    def _categorize_products(self, product_availability: Dict, all_zipcodes: Set[str]) -> tuple:
        """
        Categorize products into in_stock and out_stock based on availability across all locations.
        
        Returns:
            Tuple of (products_in_stock, products_out_stock)
        """
        products_in_stock = []
        products_out_stock = []
        
        for external_id, availability_info in product_availability.items():
            available_zipcodes = availability_info['available_zipcodes']
            in_stock_zipcodes = availability_info['in_stock_zipcodes']
            
            # Product is "in_stock" if:
            # 1. It appears in ALL configured locations
            # 2. It has in-stock variants in ALL locations where it appears
            is_in_all_locations = available_zipcodes == all_zipcodes
            is_in_stock_everywhere = in_stock_zipcodes == available_zipcodes
            
            if is_in_all_locations and is_in_stock_everywhere:
                # Product is available and in stock in ALL locations
                product_data = availability_info['product_info'].copy()
                
                # Add availability summary
                product_data['availability_summary'] = {
                    'available_in_locations': len(available_zipcodes),
                    'total_locations': len(all_zipcodes),
                    'in_stock_locations': len(in_stock_zipcodes),
                    'available_zipcodes': sorted(list(available_zipcodes)),
                    'in_stock_zipcodes': sorted(list(in_stock_zipcodes))
                }
                
                products_in_stock.append(product_data)
            else:
                # Product is NOT available in all locations or not in stock everywhere
                product_data = availability_info['product_info'].copy()
                
                # Add availability summary with reason for being out of stock
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
                
                products_out_stock.append(product_data)
        
        return products_in_stock, products_out_stock
    
    def _save_stock_files(self, products_in_stock: List[Dict], products_out_stock: List[Dict]):
        """Save the in_stock and out_stock files in both JSON and CSV formats."""
        
        # Save products_in_stock files
        self._save_json_file(products_in_stock, "products_in_stock.json")
        self._save_csv_file(products_in_stock, "products_in_stock.csv")
        
        # Save products_out_stock files
        self._save_json_file(products_out_stock, "products_out_stock.json")
        self._save_csv_file(products_out_stock, "products_out_stock.csv")
    
    def _save_json_file(self, products: List[Dict], filename: str):
        """Save products to JSON file."""
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {filename} ({len(products)} products)")
    
    def _save_csv_file(self, products: List[Dict], filename: str):
        """Save products to CSV file."""
        if not products:
            return
        
        file_path = self.output_dir / filename
        
        # Prepare CSV data
        csv_products = []
        for product in products:
            csv_product = self._prepare_product_for_csv(product)
            csv_products.append(csv_product)
        
        # Get all unique fields
        all_fields = set()
        for product in csv_products:
            all_fields.update(product.keys())
        
        # Sort fields for consistent output
        fieldnames = sorted(list(all_fields))
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_products)
        
        print(f"✅ Saved {filename} ({len(products)} products)")
    
    def _prepare_product_for_csv(self, product: Dict) -> Dict:
        """Prepare a product dictionary for CSV export."""
        csv_product = product.copy()
        
        # Convert lists to pipe-separated strings
        if 'images' in csv_product and isinstance(csv_product['images'], list):
            csv_product['images_csv'] = '|'.join(csv_product['images'])
            del csv_product['images']
        
        # Convert variants to JSON string
        if 'variants' in csv_product and isinstance(csv_product['variants'], list):
            csv_product['variants_json'] = json.dumps(csv_product['variants'], ensure_ascii=False)
            del csv_product['variants']
        
        # Convert availability_summary to JSON string
        if 'availability_summary' in csv_product and isinstance(csv_product['availability_summary'], dict):
            csv_product['availability_summary_json'] = json.dumps(csv_product['availability_summary'], ensure_ascii=False)
            del csv_product['availability_summary']
        
        return csv_product
    
    def _print_stock_statistics(self, products_in_stock: List[Dict], products_out_stock: List[Dict], all_zipcodes: Set[str]):
        """Print statistics about the stock analysis."""
        total_products = len(products_in_stock) + len(products_out_stock)
        
        print(f"\n📈 STOCK ANALYSIS RESULTS")
        print("="*60)
        print(f"Total unique products analyzed: {total_products}")
        print(f"Products available in ALL {len(all_zipcodes)} locations: {len(products_in_stock)}")
        print(f"Products NOT available in all locations: {len(products_out_stock)}")
        
        if total_products > 0:
            in_stock_percentage = (len(products_in_stock) / total_products) * 100
            print(f"Availability rate: {in_stock_percentage:.1f}%")
        
        print(f"\nFiles generated:")
        print(f"  - products_in_stock.json ({len(products_in_stock)} products)")
        print(f"  - products_in_stock.csv")
        print(f"  - products_out_stock.json ({len(products_out_stock)} products)")
        print(f"  - products_out_stock.csv")
        
        print("="*60) 