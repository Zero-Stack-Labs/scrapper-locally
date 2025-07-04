"""Product data model."""

from typing import List, Dict, Optional, Union
from datetime import datetime
import json
from .variant import Variant


class Product:
    """Product data model with clean structure."""
    
    def __init__(self, external_id: str, name: str, brand: str = ""):
        self.record_type = "product"
        self.provider_id = "www.locally.com"
        self.external_id = external_id
        self.name = name
        self.brand = brand
        self.url = ""
        self.sku = ""
        self.images: List[str] = []
        self.external_sell_price: float = 0.0
        self.currency = ""
        self.condition = ""
        self.description = ""
        self.variants: List[Dict] = []
        self.page_number: Optional[int] = None
        self.store_id = ""
        self.lat = 0.0
        self.lng = 0.0
        self.zipcode = ""
        self.store_name = ""
        self.stock_status = "unknown"
        self.available_zipcodes: List[str] = []
        self.in_stock_zipcodes: List[str] = []
        self.all_zipcodes: List[str] = []
        self.category = ""
        self.tags: List[Dict] = []
        self.options: List[Dict] = []
        self.coupon_code = ""
        self.coupon_code_discount: float = 0.0
        self.coupon_discount_type = ""
        self.restricted_brand_id: Optional[str] = None
        self.external_compare_at_price: Optional[float] = None
        self.shopify_category_id: Optional[str] = None
        self.external_discount: Optional[float] = None
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
    
    def set_store_info(self, store_id: str, lat: float, lng: float, zipcode: str, store_name: str):
        """Set store information for the product."""
        self.store_id = store_id
        self.lat = lat
        self.lng = lng
        self.zipcode = zipcode
        self.store_name = store_name
    
    def set_timestamps(self, created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        """Set timestamp information for the product."""
        self.created_at = created_at
        self.updated_at = updated_at
    
    @property
    def variants_count(self) -> int:
        """Number of variants for this product."""
        return len(self.variants)
    
    @property
    def images_count(self) -> int:
        """Number of images for this product."""
        return len(self.images)
    
    def add_variant(self, variant_data: Union[Dict, Variant]):
        """Add a variant to the product."""
        if isinstance(variant_data, Variant):
            self.variants.append(variant_data.to_dict())
        else:
            self.variants.append(variant_data)
    
    def add_variants(self, variants: List[Union[Dict, Variant]]):
        """Add multiple variants to the product."""
        for variant in variants:
            self.add_variant(variant)
    
    def get_variants_as_objects(self) -> List[Variant]:
        """Get variants as Variant objects."""
        variant_objects = []
        for variant_dict in self.variants:
            # Create Variant from stored dict data
            variant = Variant(
                name=variant_dict.get('name', ''),
                upc=variant_dict.get('upc', ''),
                page_id_variant=variant_dict.get('page_id_variant', '')
            )
            
            # Set additional properties
            variant.external_id = variant_dict.get('external_id', '')
            variant.variant_key = variant_dict.get('variant_key', '')
            variant.attributes = variant_dict.get('attributes', [])
            variant.url_variant = variant_dict.get('url_variant', '')
            variant.stock_status = variant_dict.get('stock_status', 'Not Collected')
            variant.external_quantity = variant_dict.get('external_quantity')
            variant.store_name = variant_dict.get('store_name', '')
            variant.store_address = variant_dict.get('store_address', '')
            variant.store_id = variant_dict.get('store_id', '')
            variant.variant_price = variant_dict.get('variant_price', '')
            variant.variant_currency = variant_dict.get('variant_currency', '')
            variant.stock_data = variant_dict.get('stock_data', {})
            variant.parent_product_id = variant_dict.get('parent_product_id', self.external_id)
            variant.page_number = variant_dict.get('page_number', self.page_number)
            
            variant_objects.append(variant)
        
        return variant_objects
    
    def update_variants_from_objects(self, variant_objects: List[Variant]):
        """Update variants from Variant objects."""
        self.variants = [variant.to_dict() for variant in variant_objects]
    
    def to_dict(self) -> Dict:
        """Convert product to dictionary for export."""
        return {
            "record_type": self.record_type,
            "provider_id": self.provider_id,
            "external_id": self.external_id,
            "name": self.name,
            "brand": self.brand,
            "url": self.url,
            "sku": self.sku,
            "images": self.images,
            "external_sell_price": self.external_sell_price,
            "currency": self.currency,
            "condition": self.condition,
            "description": self.description,
            "variants": self.variants,
            "variants_count": self.variants_count,
            "images_count": self.images_count,
            "page_number": self.page_number,
            "store_id": self.store_id,
            "lat": self.lat,
            "lng": self.lng,
            "zipcode": self.zipcode,
            "store_name": self.store_name,
            "stock_status": self.stock_status,
            "available_zipcodes": self.available_zipcodes,
            "in_stock_zipcodes": self.in_stock_zipcodes,
            "all_zipcodes": self.all_zipcodes,
            "category": self.category,
            "tags": self.tags,
            "options": self.options,
            "coupon_code": self.coupon_code,
            "coupon_code_discount": self.coupon_code_discount,
            "coupon_discount_type": self.coupon_discount_type,
            "restricted_brand_id": self.restricted_brand_id,
            "external_compare_at_price": self.external_compare_at_price,
            "external_discount": self.external_discount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_dict_for_csv(self) -> Dict:
        """Convert product to dictionary optimized for CSV export."""
        data = self.to_dict()
        
        data['images_csv'] = '|'.join(self.images) if self.images else ''
        data['variants_json'] = json.dumps(self.variants, ensure_ascii=False)
        
        data.pop('images', None)
        data.pop('variants', None)
        
        return data
    
    @classmethod
    def from_json_ld(cls, json_ld_data: Dict) -> Optional['Product']:
        """Create Product from JSON-LD structured data."""
        try:
            external_id = ""
            url = json_ld_data.get('url', '')
            
            if url:
                import re
                match = re.search(r'/product/(\d+)/', url)
                if match:
                    external_id = match.group(1)
            
            if not external_id:
                external_id = json_ld_data.get('sku', '') or json_ld_data.get('@id', '')
            
            name = json_ld_data.get('name', '')
            brand = json_ld_data.get('brand', {})
            
            if isinstance(brand, dict):
                brand = brand.get('name', '')
            elif isinstance(brand, str):
                brand = brand
            else:
                brand = ''
            
            if not external_id or not name:
                return None
            
            product = cls(external_id, name, brand)
            
            product.url = url
            product.sku = json_ld_data.get('sku', '')
            product.description = json_ld_data.get('description', '')
            
            offers = json_ld_data.get('offers', [])
            if offers:
                if isinstance(offers, list) and len(offers) > 0:
                    first_offer = offers[0]
                    try:
                        product.external_sell_price = float(first_offer.get('price', 0))
                    except (ValueError, TypeError):
                        product.external_sell_price = 0.0
                    product.currency = first_offer.get('priceCurrency', '')
                    product.condition = first_offer.get('itemCondition', '')
                elif isinstance(offers, dict):
                    try:
                        product.external_sell_price = float(offers.get('price', 0))
                    except (ValueError, TypeError):
                        product.external_sell_price = 0.0
                    product.currency = offers.get('priceCurrency', '')
                    product.condition = offers.get('itemCondition', '')
            
            images = json_ld_data.get('image', [])
            if isinstance(images, str):
                product.images = [images]
            elif isinstance(images, list):
                product.images = images
            
            return product
            
        except Exception:
            return None 