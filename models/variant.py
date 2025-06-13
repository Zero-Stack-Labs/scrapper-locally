"""Variant data model."""

from typing import List, Dict, Optional
import json
import re


class Variant:
    """Product variant data model with stock information."""
    
    def __init__(self, name: str, upc: str = "", page_id_variant: str = ""):
        self.record_type = "variant"
        self.provider_id = "www.locally.com"
        self.name = name
        self.upc = upc
        self.page_id_variant = page_id_variant
        self.variant_key = ""
        self.external_id = ""
        self.attributes: List[Dict] = []
        self.url_variant = ""
        
        # Stock information
        self.stock_status = "Not Collected"
        self.external_quantity: Optional[int] = None
        self.store_name = ""
        self.store_address = ""
        self.store_id = ""
        self.variant_price = ""
        self.variant_currency = ""
        self.stock_data: Dict = {}
        
        # Parent product reference
        self.parent_product_id: Optional[str] = None
        self.page_number: Optional[int] = None
        
        # Generate variant key and external_id
        self._generate_identifiers()
    
    def _generate_identifiers(self):
        """Generate variant_key and external_id based on available data."""
        variant_key_parts = []
        
        if self.upc:
            variant_key_parts.append(self.upc)
            self.external_id = f"variant_{self.upc}"
        elif self.page_id_variant:
            variant_key_parts.append(self.page_id_variant)
            self.external_id = f"variant_{self.page_id_variant}"
        else:
            # Create a slug from the name
            base_name_slug = re.sub(r'[^\w]+', '_', self.name).strip('_').lower()
            variant_key_parts.append(base_name_slug)
            
            # Add slugs of attributes
            for attr in self.attributes:
                attr_slug = re.sub(r'[^\w]+', '_', attr['value']).strip('_').lower()
                variant_key_parts.append(attr_slug)
            
            self.variant_key = "-".join(variant_key_parts)
            self.external_id = f"variant_{self.variant_key}"
        
        self.variant_key = "-".join(variant_key_parts)
    
    def extract_attributes_from_name(self):
        """Extract attributes from variant name (content within parentheses)."""
        self.attributes = []
        
        # Extract values within parentheses
        parentheses_match = re.search(r'\(([^)]+)\)', self.name)
        if parentheses_match:
            content = parentheses_match.group(1)
            # Split by commas to get individual attributes
            attribute_values = [attr.strip() for attr in content.split(',') if attr.strip()]
            
            # Assign generic category names
            for i, val in enumerate(attribute_values):
                self.attributes.append({
                    "category_name": f"Attribute {i+1}",
                    "value": val
                })
        
        # Regenerate identifiers with new attributes
        self._generate_identifiers()
    
    def set_stock_url(self, product_id: str, store_id: str = ""):
        """Generate the stock API URL for this variant."""
        if product_id and self.upc and store_id:
            self.url_variant = f"https://www.locally.com/product_stock/{product_id}?store={store_id}&sort=pop&upc={self.upc}&store={store_id}"
    
    def update_stock_info(self, stock_data: Dict):
        """Update stock information from API response."""
        self.stock_data = stock_data
        
        if stock_data:
            self.stock_status = "Available" if stock_data.get('in_stock', False) else "Out of Stock"
            self.external_quantity = stock_data.get('quantity', 0)
            self.variant_price = str(stock_data.get('price', ''))
            self.variant_currency = stock_data.get('currency', '')
            
            # Store information
            store_info = stock_data.get('store', {})
            self.store_name = store_info.get('name', '')
            self.store_address = store_info.get('address', '')
            self.store_id = str(store_info.get('id', ''))
        else:
            self.stock_status = "Not Available"
    
    def to_dict(self) -> Dict:
        """Convert variant to dictionary for export."""
        return {
            "record_type": self.record_type,
            "provider_id": self.provider_id,
            "external_id": self.external_id,
            "name": self.name,
            "variant_key": self.variant_key,
            "attributes": self.attributes,
            "upc": self.upc,
            "page_id_variant": self.page_id_variant,
            "url_variant": self.url_variant,
            "stock_status": self.stock_status,
            "external_quantity": self.external_quantity,
            "store_name": self.store_name,
            "store_address": self.store_address,
            "store_id": self.store_id,
            "variant_price": self.variant_price,
            "variant_currency": self.variant_currency,
            "stock_data": self.stock_data,
            "parent_product_id": self.parent_product_id,
            "page_number": self.page_number
        }
    
    def to_dict_for_csv(self) -> Dict:
        """Convert variant to dictionary optimized for CSV export."""
        data = self.to_dict()
        
        # Convert attributes list to pipe-separated string for CSV
        data['attributes_csv'] = '|'.join([
            f"{attr.get('category_name', '')}:{attr.get('value', '')}"
            for attr in self.attributes
        ]) if self.attributes else ''
        
        # Convert stock_data to JSON string
        data['stock_json'] = json.dumps(self.stock_data, ensure_ascii=False)
        
        # Remove the original list/dict fields for CSV
        data.pop('attributes', None)
        data.pop('stock_data', None)
        
        return data
    
    @classmethod
    def from_json_data(cls, variant_data: Dict, product_id: str = "") -> 'Variant':
        """Create Variant from JSON data."""
        name = variant_data.get('name', '')
        upc = variant_data.get('upc', '')
        page_id_variant = variant_data.get('page_id_variant', '')
        
        variant = cls(name, upc, page_id_variant)
        variant.extract_attributes_from_name()
        
        if product_id:
            variant.set_stock_url(product_id)
        
        return variant 