"""Product data model."""

from typing import List, Dict, Optional
import json


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
    
    @property
    def variants_count(self) -> int:
        """Number of variants for this product."""
        return len(self.variants)
    
    @property
    def images_count(self) -> int:
        """Number of images for this product."""
        return len(self.images)
    
    def add_variant(self, variant_data: Dict):
        """Add a variant to the product."""
        self.variants.append(variant_data)
    
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
            "page_number": self.page_number
        }
    
    def to_dict_for_csv(self) -> Dict:
        """Convert product to dictionary optimized for CSV export."""
        data = self.to_dict()
        
        # Convert lists to pipe-separated strings for CSV
        data['images_csv'] = '|'.join(self.images) if self.images else ''
        data['variants_json'] = json.dumps(self.variants, ensure_ascii=False)
        
        # Remove the original list fields for CSV
        data.pop('images', None)
        data.pop('variants', None)
        
        return data
    
    @classmethod
    def from_json_ld(cls, json_data: Dict) -> Optional['Product']:
        """Create Product from JSON-LD data."""
        if json_data.get('@type') != 'Product':
            return None
        
        # Extract product ID from URL
        url = json_data.get('url', '')
        external_id = ""
        if url:
            import re
            match = re.search(r'/product/(\d+)/', url)
            if match:
                external_id = match.group(1)
        
        if not external_id:
            return None
        
        name = json_data.get('name', '')
        
        # Extract brand
        brand_data = json_data.get('brand', {})
        if isinstance(brand_data, dict):
            brand = brand_data.get('name', '')
        else:
            brand = str(brand_data)
        
        product = cls(external_id, name, brand)
        product.url = url
        product.sku = json_data.get('sku', '')
        
        # Extract image
        image = json_data.get('image', '')
        if image:
            product.images = [image]
        
        # Extract price from offers
        offers = json_data.get('offers', [])
        if offers and isinstance(offers, list):
            first_offer = offers[0]
            try:
                product.external_sell_price = float(first_offer.get('price', 0))
            except (ValueError, TypeError):
                product.external_sell_price = 0.0
            product.currency = first_offer.get('priceCurrency', '')
            product.condition = first_offer.get('itemCondition', '')
        
        return product 