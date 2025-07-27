from typing import List, Dict, Set
from collections import defaultdict
from utils.logging_config import get_logger
from models.product import Product

logger = get_logger(__name__)


class FootlockerStockAnalyzer:
    
    def __init__(self):
        self.logger = logger
    
    def analyze_multi_location_stock(self, all_products: List[Product], all_zipcodes: List[str]) -> List[Product]:
        if not all_products:
            return []
        
        all_zipcodes_set = set(all_zipcodes)
        logger.info(f"Analizando stock para {len(all_products)} productos across zipcodes: {sorted(all_zipcodes)}")
        
        product_by_external_id = defaultdict(list)
        for product in all_products:
            product_by_external_id[product.external_id].append(product)
        
        unified_products = []
        
        for external_id, product_variants in product_by_external_id.items():
            unified_product = self._create_unified_product(product_variants, all_zipcodes_set)
            if unified_product:
                unified_products.append(unified_product)
        
        logger.info(f"Análisis completado: {len(unified_products)} productos unificados")
        return unified_products
    
    def _create_unified_product(self, product_variants: List[Product], all_zipcodes: Set[str]) -> Product:
        if not product_variants:
            return None
        
        base_product = product_variants[0]
        
        available_zipcodes = set()
        in_stock_zipcodes = set()
        
        for product in product_variants:
            if product.zipcode:
                available_zipcodes.add(product.zipcode)
                
                if self._product_has_stock(product):
                    in_stock_zipcodes.add(product.zipcode)
        
        unified_product = Product(
            external_id=base_product.external_id,
            name=base_product.name,
            brand=base_product.brand
        )
        
        for attr in ['provider_id', 'url', 'sku', 'external_sell_price', 'currency', 'condition', 'description', 'images', 'variants', 'store_id', 'lat', 'lng']:
            if hasattr(base_product, attr):
                setattr(unified_product, attr, getattr(base_product, attr))
        
        unified_product.zipcode = base_product.zipcode
        unified_product.available_zipcodes = sorted(list(available_zipcodes))
        unified_product.in_stock_zipcodes = sorted(list(in_stock_zipcodes))
        unified_product.all_zipcodes = sorted(list(all_zipcodes))
        
        is_available_everywhere = available_zipcodes == all_zipcodes
        is_in_stock_everywhere = in_stock_zipcodes == available_zipcodes and len(in_stock_zipcodes) > 0
        
        if is_available_everywhere and is_in_stock_everywhere:
            unified_product.stock_status = 'in_stock'
        else:
            unified_product.stock_status = 'out_of_stock'
        
        logger.debug(f"Producto {base_product.external_id}: disponible en {len(available_zipcodes)}/{len(all_zipcodes)} ubicaciones, en stock en {len(in_stock_zipcodes)} ubicaciones - Status: {unified_product.stock_status}")
        
        return unified_product
    
    def _product_has_stock(self, product: Product) -> bool:
        if not product.variants:
            return product.external_sell_price and product.external_sell_price > 0
        
        for variant in product.variants:
            if isinstance(variant, dict):
                stock_status = variant.get('stock_status', '').lower()
                if stock_status in ['in stock', 'available', 'in_stock']:
                    return True
        
        return False 