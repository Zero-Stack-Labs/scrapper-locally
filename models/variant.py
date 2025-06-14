"""Variant data model."""

from typing import Dict, Optional
import re


class Variant:
    """Product variant data model."""
    
    def __init__(self, name: str, upc: str = ""):
        self.name = name
        self.upc = upc
        self.price = 0.0
        self.attributes: Dict[str, str] = {}
        self.stock_status = "unknown"
        self.image = ""
        # Additional fields to be filled later
        self.external_product_id = ""
        self.sku = ""
    
    def set_attributes(self, attributes: Dict[str, str]):
        self.attributes = attributes
    
    def set_price(self, price_value):
        """Set variant price from various formats."""
        if isinstance(price_value, (int, float)):
            self.price = float(price_value)
        elif isinstance(price_value, str):
            try:
                # Remove currency symbols and convert to float
                price_str = price_value.replace('$', '').replace(',', '').strip()
                self.price = float(price_str)
            except (ValueError, TypeError):
                self.price = 0.0
        else:
            self.price = 0.0
    
    def set_stock_status(self, status: str):
        """Set stock status for the variant."""
        self.stock_status = status if status else "unknown"
    
    def set_image(self, image_url: str):
        """Set image URL for the variant."""
        self.image = image_url if image_url else ""
    
    def set_parent_info(self, external_product_id: str, sku: str):
        """Set parent product information."""
        self.external_product_id = external_product_id if external_product_id else ""
        self.sku = sku if sku else ""
    
    def to_dict(self, fallback_image: str = "") -> Dict:
        """Convert variant to simple dictionary format."""
        # Use fallback image if variant has no image
        final_image = self.image if self.image.strip() else fallback_image
        
        return {
            "upc": self.upc,
            "sku": self.sku,
            "name": self.name,
            "price": self.price,
            "external_product_id": self.external_product_id,
            "stock_status": self.stock_status,
            "attributes": self.attributes,
            "image": final_image
        }
    
    @classmethod
    def from_json_data(cls, variant_data: Dict, product_sku: str = "") -> 'Variant':
        """Create variant from JSON data."""
        name = variant_data.get('name', '')
        upc = variant_data.get('gtin', variant_data.get('upc', ''))
        
        variant = cls(name=name, upc=upc)
        
        # Set price from offers
        offers = variant_data.get('offers', {})
        if isinstance(offers, dict):
            price_str = offers.get('price', '0')
            variant.set_price(price_str)
        
        return variant 