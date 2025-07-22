from typing import Dict, List, Optional
import re
from urllib.parse import urlparse
from models.product import Product
from models.variant import Variant
from utils.logging_config import get_logger

logger = get_logger(__name__)

class FootlockerMapper:
    
    @staticmethod
    def map_api_product_to_product(product_data: Dict, base_url: str,
                                   store_id: str = '', latitude: float = 0.0,
                                   longitude: float = 0.0, zipcode: str = '') -> Optional[Product]:
        try:
            external_id = product_data.get('sku', '')
            name = product_data.get('name', '')
            
            if not external_id or not name:
                logger.warning(f"Producto sin ID o nombre: {product_data}")
                return None
            
            product = Product(external_id=external_id, name=name)
            
            product.store_id = store_id
            product.lat = latitude
            product.lng = longitude
            product.zipcode = zipcode
            
            zip_array = [zipcode] if zipcode else []
            product.available_zipcodes = zip_array
            product.in_stock_zipcodes = zip_array
            product.all_zipcodes = zip_array
            
            parsed_url = urlparse(base_url)
            domain = parsed_url.netloc
            store_name = domain.replace('www.', '').replace('.com', '')
            
            product.store_name = store_name
            product.provider_id = domain
            product.url = f"{base_url}/product/~/{external_id}.html"
            product.sku = product_data.get('baseProduct', external_id)
            product.brand = FootlockerMapper._extract_brand_from_name(name)
            
            price_info = product_data.get('price', {})
            product.external_sell_price = price_info.get('value', 0.0)
            product.currency = "USD"
            
            original_price_info = product_data.get('originalPrice', {})
            if original_price_info and original_price_info.get('value', 0) > price_info.get('value', 0):
                product.external_compare_at_price = original_price_info.get('value')
                
            badges = product_data.get('badges', {})
            product.condition = "new" if badges.get('isNewProduct', False) else "unknown"
            
            images = product_data.get('images', [])
            if images:
                for img in images:
                    if img.get('format') == 'large' and img.get('url'):
                        product.images.append(img['url'])
            
            review_ratings = product_data.get('reviewRatings', {})
            if review_ratings:
                product.description = f"Rating: {review_ratings.get('rating', 0)}/5 ({review_ratings.get('reviews', 0)} reviews)"
            
            base_options = product_data.get('baseOptions', [])
            if base_options:
                for option in base_options:
                    selected = option.get('selected', {})
                    if selected.get('style'):
                        product.options.append({
                            'name': 'style',
                            'value': selected['style']
                        })
            
            if badges.get('isSale', False):
                product.tags.append({'name': 'sale', 'value': 'true'})
            if badges.get('isNewProduct', False):
                product.tags.append({'name': 'new', 'value': 'true'})
            if badges.get('isPromoted', False):
                product.tags.append({'name': 'promoted', 'value': 'true'})
            
            return product
            
        except Exception as e:
            logger.error(f"Error al mapear producto de API Footlocker: {e}")
            return None

    @staticmethod
    def map_product_details_to_variants(offers: List[Dict], product_id: str, product_sku: str, 
                                      product_name: str, fallback_image: str = "") -> List[Dict]:
        variants = []
        
        for offer in offers:
            variant_sku = offer.get('sku', '')
            
            attributes = FootlockerMapper._extract_variant_attributes(variant_sku, offer)
            
            size = attributes.get('size', '')
            color = attributes.get('color', '')
            
            variant_name_parts = [product_name]
            if color:
                variant_name_parts.append(f"Color: {color}")
            if size:
                variant_name_parts.append(f"Size: {size}")
            
            variant_name = " - ".join(variant_name_parts)
            
            variant = Variant(name=variant_name, upc=variant_sku)
            variant.set_price(offer.get('price', 0))
            variant.set_parent_info(product_id, product_sku)
            
            availability = offer.get('availability', '')
            stock_status = "in_stock" if availability == 'InStock' else "out_of_stock"
            
            # Si el precio es <= 0, marcar como out_of_stock
            if variant.price <= 0:
                stock_status = "out_of_stock"
            
            variant.set_stock_status(stock_status)
            
            # Convert attributes to Locally format (capitalized)
            locally_attributes = {}
            if color:
                locally_attributes['Color'] = color
            if size:
                locally_attributes['Size'] = size
            # Keep additional attributes with original casing for technical info
            for key, value in attributes.items():
                if key not in ['color', 'size', 'variant_sku', 'base_sku']:
                    locally_attributes[key] = value
            
            variant.set_attributes(locally_attributes)
            
            # Convert to dict and fix the product_id field for Locally format
            variant_dict = variant.to_dict(fallback_image)
            variant_dict['product_id'] = variant_dict.pop('external_product_id')
            
            variants.append(variant_dict)
        
        return variants

    @staticmethod
    def _extract_variant_attributes(variant_sku: str, variant_info: dict = None) -> dict:
        attributes = {}
        
        # Extract size from SKU
        size_match = re.search(r'-(\d+\.?\d*)$', variant_sku)
        if size_match:
            attributes['size'] = size_match.group(1)
        
        # Extract color - first try from variant_info, then fallback to SKU mapping
        if variant_info and variant_info.get('color'):
            attributes['color'] = variant_info['color']
        
        # Extract gender from SKU prefix
        gender_patterns = {
            'W': 'Women',
            'M': 'Men', 
            'C': 'Kids',
            'D': 'Unisex'
        }
        
        first_char = variant_sku[0] if variant_sku else ''
        if first_char in gender_patterns:
            attributes['gender'] = gender_patterns[first_char]
        
        # Add SKU information
        attributes['variant_sku'] = variant_sku
        base_sku = re.sub(r'-\d+\.?\d*$', '', variant_sku)
        attributes['base_sku'] = base_sku
        
        # Extract model from base SKU
        if len(base_sku) >= 4:
            attributes['model'] = base_sku[1:5]
        
        return attributes

    @staticmethod
    def _extract_brand_from_name(name: str) -> str:
        common_brands = ['Nike', 'Adidas', 'Puma', 'Reebok', 'New Balance', 'Converse', 'Vans', 'Jordan']
        
        name_upper = name.upper()
        for brand in common_brands:
            if brand.upper() in name_upper:
                return brand
        
        first_word = name.split()[0] if name.split() else ""
        return first_word

    @staticmethod
    def _extract_size_from_sku(sku: str) -> str:
        if not sku:
            return ""
        
        parts = sku.split('-')
        if len(parts) >= 2:
            return parts[-1]
        return "" 