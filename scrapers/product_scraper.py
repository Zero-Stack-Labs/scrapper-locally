from typing import List, Optional, Dict
from .base_scraper import BaseScraper
from models.product import Product
from models.variant import Variant
from bs4 import BeautifulSoup
import re
import json
import requests
import concurrent.futures
import threading
import logging

logger = logging.getLogger(__name__)

class ProductScraper(BaseScraper):
    
    def get_product_details(self, product_url: str) -> Optional[Product]:
        try:
            response = self.session.get(product_url, headers=self.headers)
            if response.status_code == 200:
                return self.parse_product_details_page(response.text, product_url)
        except requests.RequestException as e:
            logger.error(f"Error making request to {product_url}: {e}")
        return None
    
    def parse_product_details_page(self, html_content: str, product_url: str) -> Optional[Product]:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        canonical_link = soup.find('link', {'rel': 'canonical'})
        canonical_url = canonical_link.get('href') if canonical_link else ""
        
        external_id = ""
        if canonical_url:
            match = re.search(r'/product/(\d+)/', canonical_url)
            if match:
                external_id = match.group(1)
        
        if not external_id:
            return None
        
        name, brand, sku, images, price, currency = self._extract_complete_product_info_from_json_ld(soup)
        if not name:
            return None
        
        product = Product(external_id, name, brand)
        product.url = product_url
        product.sku = sku  # Establecer el SKU extraído de JSON-LD
        product.images = images
        product.external_sell_price = price
        product.currency = currency
        
        # Extract description from product information section
        description = self._extract_description_from_page(soup)
        product.description = description
        
        variants = self._extract_variants_from_html(soup, product)
        for variant in variants:
            variant.set_parent_info(product.external_id, product.sku)
            fallback_image = product.images[0] if product.images else ""
            product.add_variant(variant.to_dict(fallback_image=fallback_image))
        
        return product
    
    def get_product_details_batch(self, product_urls: List[str], max_workers: int = 5) -> List[Product]:
        logger.info(f"Getting details for {len(product_urls)} products with {max_workers} workers...")
        
        local = threading.local()
        
        def process_url(url):
            if not hasattr(local, 'session'):
                local.session = requests.Session()
                local.session.headers.update(self.headers)
            
            try:
                logger.debug(f"Processing URL: {url}")
                response = local.session.get(url, headers=self.headers)
                logger.debug(f"Response status for {url}: {response.status_code}")
                
                if response.status_code == 200:
                    product = self.parse_product_details_page(response.text, url)
                    if product:
                        logger.debug(f"✅ Successfully parsed product {product.external_id} with {len(product.variants)} variants")
                    else:
                        logger.warning(f"⚠️ Failed to parse product from {url}")
                    return product
                else:
                    logger.warning(f"❌ Non-200 status code {response.status_code} for {url}")
            except Exception as exc:
                logger.error(f'Error processing product {url}: {exc}')
            return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(process_url, product_urls))
        
        detailed_products = [p for p in results if p is not None]
        logger.info(f"Successfully scraped {len(detailed_products)}/{len(product_urls)} detailed products")
        
        # Log summary of variants
        total_variants = sum(len(p.variants) for p in detailed_products)
        if detailed_products:
            logger.info(f"Total variants found: {total_variants}")
            products_with_variants = sum(1 for p in detailed_products if len(p.variants) > 0)
            logger.info(f"Products with variants: {products_with_variants}/{len(detailed_products)}")
        
        return detailed_products
    
    def _extract_complete_product_info_from_json_ld(self, soup: BeautifulSoup) -> tuple:
        """Extract complete product info from JSON-LD scripts"""
        for script in soup.find_all('script', {'type': 'application/ld+json'}):
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, list):
                    for item in json_data:
                        if item.get('@type') == 'Product':
                            name = item.get('name', '')
                            brand_data = item.get('brand', {})
                            brand = brand_data.get('name', '') if isinstance(brand_data, dict) else str(brand_data)
                            sku = item.get('sku', '')
                            
                            # Extract images
                            images = []
                            image_data = item.get('image', [])
                            if isinstance(image_data, str):
                                images = [image_data]
                            elif isinstance(image_data, list):
                                images = image_data
                            
                            # Extract price and currency from offers
                            price = 0.0
                            currency = ""
                            offers = item.get('offers', [])
                            if offers:
                                if isinstance(offers, list) and len(offers) > 0:
                                    first_offer = offers[0]
                                    try:
                                        price = float(first_offer.get('price', 0))
                                    except (ValueError, TypeError):
                                        price = 0.0
                                    currency = first_offer.get('priceCurrency', '')
                                elif isinstance(offers, dict):
                                    try:
                                        price = float(offers.get('price', 0))
                                    except (ValueError, TypeError):
                                        price = 0.0
                                    currency = offers.get('priceCurrency', '')
                            
                            return name, brand, sku, images, price, currency
                elif json_data.get('@type') == 'Product':
                    name = json_data.get('name', '')
                    brand_data = json_data.get('brand', {})
                    brand = brand_data.get('name', '') if isinstance(brand_data, dict) else str(brand_data)
                    sku = json_data.get('sku', '')
                    
                    # Extract images
                    images = []
                    image_data = json_data.get('image', [])
                    if isinstance(image_data, str):
                        images = [image_data]
                    elif isinstance(image_data, list):
                        images = image_data
                    
                    # Extract price and currency from offers
                    price = 0.0
                    currency = ""
                    offers = json_data.get('offers', [])
                    if offers:
                        if isinstance(offers, list) and len(offers) > 0:
                            first_offer = offers[0]
                            try:
                                price = float(first_offer.get('price', 0))
                            except (ValueError, TypeError):
                                price = 0.0
                            currency = first_offer.get('priceCurrency', '')
                        elif isinstance(offers, dict):
                            try:
                                price = float(offers.get('price', 0))
                            except (ValueError, TypeError):
                                price = 0.0
                            currency = offers.get('priceCurrency', '')
                    
                    return name, brand, sku, images, price, currency
            except (json.JSONDecodeError, TypeError):
                continue
        return "", "", "", [], 0.0, ""
    
    def _extract_description_from_page(self, soup: BeautifulSoup) -> str:
        """Extract product description from the information section."""
        description_parts = []
        
        # Extract from pdp-information-content
        info_content = soup.find('p', class_='pdp-information-content')
        if info_content:
            description_parts.append(info_content.get_text(strip=True))
        
        # Extract from pdp-short-description if exists
        short_desc = soup.find('div', class_='pdp-short-description')
        if short_desc:
            description_parts.append(short_desc.get_text(strip=True))
        
        return "\n".join(description_parts)
    
    def _extract_variants_from_html(self, soup: BeautifulSoup, product: Product) -> List[Variant]:
        """
        Extract comprehensive variant information from the product page.
        Completely dynamic approach - no hardcoded assumptions about attribute types.
        """
        stock_status = self._extract_stock_status_from_page(soup)
        
        # Method 1: Try JavaScript data (lclyPdpData) + dynamic form selectors
        variant_dicts = self._extract_variants_from_javascript_data(soup, product.external_id, stock_status, product.sku)
        
        if not variant_dicts:
            # Method 2: Pure HTML extraction from form selectors and variant containers
            variant_dicts = self._extract_variants_from_html_structure(soup, product.external_id, stock_status, product.sku)
        
        if not variant_dicts:
            # Method 3: Create default variant
            default_variant_dict = self._create_default_variant(soup, product.external_id, stock_status, product.sku)
            if default_variant_dict:
                variant_dicts = [default_variant_dict]
        
        # Filter variants based on image availability
        variant_dicts = self._filter_variants_by_image(variant_dicts)
        
        # Convert dict variants to Variant objects
        variants = []
        for variant_dict in variant_dicts:
            variant = Variant(
                name=variant_dict.get('name', ''),
                upc=variant_dict.get('upc', '')
            )
            variant.price = variant_dict.get('price', 0.0)
            variant.stock_status = variant_dict.get('stock_status', 'unknown')
            variant.image = variant_dict.get('image', '')
            variant.set_attributes(variant_dict.get('attributes', {}))
            variant.set_parent_info(product.external_id, product.sku)
            variants.append(variant)
        
        return variants

    def _extract_stock_status_from_page(self, soup: BeautifulSoup) -> str:
        """Extract stock status from the product page."""
        # Look for stock status banner
        stock_banner = soup.find('div', class_='stock-status-banner')
        if stock_banner:
            status_text = stock_banner.get_text(strip=True).lower()
            
            if 'not in stock' in status_text:
                return 'out_of_stock'
            elif 'contact a dealer' in status_text:
                return 'contact_dealer'
            elif 'in stock' in status_text:
                return 'in_stock'
            else:
                return 'unknown'
        
        # Look for other stock indicators
        stock_indicators = soup.find_all(text=True)
        for text in stock_indicators:
            text_lower = text.strip().lower()
            if 'in stock' in text_lower:
                return 'in_stock'
            elif 'out of stock' in text_lower:
                return 'out_of_stock'
        
        return 'unknown'

    def _extract_variants_from_javascript_data(self, soup: BeautifulSoup, product_id: str, stock_status: str, sku: str) -> List[Dict]:
        """Extract variants using JavaScript lclyPdpData + dynamic form selectors."""
        
        # Extract JavaScript data
        lcly_data = self._extract_lcly_pdp_data(soup)
        if not lcly_data:
            return []
        
        # Get UPCs from multiple sources
        all_upcs = lcly_data.get('all_upcs_carried', [])
        upc_prices = lcly_data.get('upc_prices', {})
        
        # Use UPCs from upc_prices keys when all_upcs_carried is empty
        if not all_upcs and upc_prices:
            all_upcs = list(upc_prices.keys())
        
        if not all_upcs:
            return []
        
        # Extract dynamic attributes from form selectors
        attribute_mappings = self._extract_dynamic_attribute_mappings(soup)
        
        # Extract variant names from HTML (use real names instead of generating them)
        upc_to_name = self._extract_variant_names_from_html(soup)
        
        # Extract variant images from HTML
        upc_to_image = self._extract_variant_images_from_html(soup)
        
        # Get product name for fallback
        product_name = self._extract_product_name_from_page(soup)
        
        # Create variants for each UPC
        variants = []
        for upc in all_upcs:
            if isinstance(upc, str) and upc.strip():
                upc = upc.strip()
                
                # Get price from upc_prices
                price_info = upc_prices.get(upc, {})
                price = self._extract_price_from_upc_data(price_info)
                
                # Get all attributes for this UPC
                attributes = {}
                for attr_name, upc_mapping in attribute_mappings.items():
                    if upc in upc_mapping:
                        attributes[attr_name] = upc_mapping[upc]
                
                # Use real variant name from HTML, or generate as fallback
                variant_name = upc_to_name.get(upc)
                if not variant_name:
                    variant_name = self._generate_variant_name(product_name, attributes)
                
                # Detect variant-specific stock status
                variant_stock_status = self._detect_variant_stock_status(soup, upc, attributes, stock_status)
                
                # Create variant
                variant = {
                    'upc': upc,
                    'sku': sku,
                    'name': variant_name,
                    'price': price,
                    'product_id': product_id,
                    'stock_status': variant_stock_status,
                    'attributes': attributes,
                    'image': upc_to_image.get(upc, '')  # Always include image field, empty if not found
                }
                
                variants.append(variant)
        
        return variants

    def _extract_variants_from_html_structure(self, soup: BeautifulSoup, product_id: str, stock_status: str, sku: str) -> List[Dict]:
        """Extract variants directly from HTML structure when JavaScript data is not available."""
        
        variants = []
        base_price = self._extract_price_from_page(soup, soup)
        
        # Method 1: Extract from any select elements with UPC data
        variants = self._extract_from_dynamic_selectors(soup, product_id, base_price, stock_status, sku)
        
        if not variants:
            # Method 2: Extract from variant image containers
            variants = self._extract_from_variant_containers(soup, product_id, base_price, stock_status, sku)
        
        return variants

    def _extract_lcly_pdp_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract lclyPdpData from JavaScript."""
        
        # Find ALL script tags (with or without type attribute)
        script_tags = soup.find_all('script')
        
        for i, script in enumerate(script_tags):
            if script.string and 'lclyPdpData' in script.string:
                script_content = script.string
                
                # Try multiple regex patterns to extract lclyPdpData
                patterns = [
                    r'var lclyPdpData = ({.*?});',  # Original pattern
                    r'lclyPdpData = ({.*?});',      # Without var
                    r'var lclyPdpData=({.*?});',    # No spaces
                    r'lclyPdpData=({.*?});',        # No var, no spaces
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, script_content, re.DOTALL)
                    if match:
                        try:
                            lcly_data = json.loads(match.group(1))
                            
                            # Log what we found
                            all_upcs = lcly_data.get('all_upcs_carried', [])
                            upc_prices = lcly_data.get('upc_prices', {})
                            
                            return lcly_data
                        except json.JSONDecodeError as e:
                            continue
        
        return None 

    def _extract_dynamic_attribute_mappings(self, soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
        """
        Extract attribute mappings (UPC -> attribute value) for all available attributes.
        Completely dynamic - detects any attribute type automatically.
        """
        attribute_mappings = {}
        
        # Find all select elements that might contain variant data
        selects = soup.find_all('select')
        
        for select in selects:
            # Determine attribute name dynamically
            attr_name = self._determine_dynamic_attribute_name(select)
            if not attr_name:
                continue
            
            # Extract UPC mappings for this attribute
            upc_mapping = {}
            options = select.find_all('option')
            
            for option in options:
                option_name = option.get_text(strip=True)
                option_upcs = option.get('data-upcs', '')
                
                if option_name and option_upcs:
                    # Parse UPCs
                    upcs = [upc.strip() for upc in option_upcs.split(',') if upc.strip()]
                    
                    # Map each UPC to this attribute value
                    for upc in upcs:
                        upc_mapping[upc] = option_name
            
            if upc_mapping:
                attribute_mappings[attr_name] = upc_mapping
        
        return attribute_mappings

    def _determine_dynamic_attribute_name(self, select) -> str:
        """
        Dynamically determine the attribute name from a select element.
        Completely generic approach.
        """
        # Method 1: Extract from aria-label
        aria_label = select.get('aria-label', '')
        if aria_label:
            if aria_label.lower().startswith('choose '):
                # "Choose Color" -> "Color"
                return aria_label[7:].strip().title()
            elif 'choose' in aria_label.lower():
                # Extract the word after 'choose'
                parts = aria_label.lower().split()
                try:
                    choose_idx = parts.index('choose')
                    if choose_idx + 1 < len(parts):
                        return parts[choose_idx + 1].title()
                except ValueError:
                    pass
        
        # Method 2: Extract from class names
        select_classes = ' '.join(select.get('class', []))
        
        # Look for patterns in class names
        if 'color' in select_classes.lower():
            return 'Color'
        elif 'size' in select_classes.lower():
            return 'Size'
        elif 'style' in select_classes.lower():
            return 'Style'
        elif 'material' in select_classes.lower():
            return 'Material'
        elif 'variant' in select_classes.lower():
            return 'Variant'
        
        # Method 3: Look for associated labels (skip for now since we need soup)
        # This would require the soup parameter which we don't have here
        
        # Method 4: Analyze option content to infer type
        options = select.find_all('option')
        if options:
            sample_options = [opt.get_text(strip=True).lower() for opt in options[:3]]
            
            # Check for common patterns
            color_keywords = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'grey', 'brown']
            if any(any(color in opt for color in color_keywords) for opt in sample_options):
                return 'Color'
            
            size_keywords = ['small', 'medium', 'large', 'xs', 'xl', 'm', 'l', 's']
            if any(any(size in opt for size in size_keywords) for opt in sample_options):
                return 'Size'
            
            # Check for size patterns (numbers, measurements)
            import re
            size_patterns = [r'\d+', r'[XSML]+', r'\d+[WM]\d+']
            if any(any(re.search(pattern, opt) for pattern in size_patterns) for opt in sample_options):
                return 'Size'
        
        # If we can't determine the type, skip this selector
        return None

    def _extract_price_from_upc_data(self, price_info: Dict) -> float:
        """Extract price from UPC price information."""
        price = 0.0
        try:
            price = float(price_info.get('unit_msrp', 0))
            if price == 0:
                price = float(price_info.get('sale_price', 0))
            if price == 0:
                price = float(price_info.get('price', 0))
        except (ValueError, TypeError):
            price = 0.0
        return price

    def _extract_from_dynamic_selectors(self, soup: BeautifulSoup, product_id: str, base_price: float, stock_status: str, sku: str) -> List[Dict]:
        """
        Extract variants from any selectors dynamically, detecting attribute types automatically.
        Completely generic - no hardcoded assumptions about attribute types.
        """
        
        # Use the same extraction logic as in JavaScript method
        attribute_mappings = self._extract_dynamic_attribute_mappings(soup)
        
        if not attribute_mappings:
            return []
        
        # Collect all unique UPCs across all attributes
        all_upcs = set()
        for upc_mapping in attribute_mappings.values():
            all_upcs.update(upc_mapping.keys())
        
        # Extract variant names from HTML
        upc_to_name = self._extract_variant_names_from_html(soup)
        
        # Extract variant images from HTML
        upc_to_image = self._extract_variant_images_from_html(soup)
        
        # Get product name for fallback
        product_name = self._extract_product_name_from_page(soup)
        
        # Create variants for each UPC
        variants = []
        for upc in all_upcs:
            # Find all attributes for this UPC
            attributes = {}
            for attr_name, upc_mapping in attribute_mappings.items():
                if upc in upc_mapping:
                    attributes[attr_name] = upc_mapping[upc]
            
            # Use real variant name from HTML, or generate as fallback
            variant_name = upc_to_name.get(upc)
            if not variant_name:
                variant_name = self._generate_variant_name(product_name, attributes)
            
            # Detect variant-specific stock status
            variant_stock_status = self._detect_variant_stock_status(soup, upc, attributes, stock_status)
            
            variant = {
                'upc': upc,
                'sku': sku,
                'name': variant_name,
                'price': base_price,
                'product_id': product_id,
                'stock_status': variant_stock_status,
                'attributes': attributes,
                'image': upc_to_image.get(upc, '')  # Always include image field, empty if not found
            }
            
            variants.append(variant)
        
        return variants

    def _extract_from_variant_containers(self, soup: BeautifulSoup, product_id: str, base_price: float, stock_status: str, sku: str) -> List[Dict]:
        """Extract variants from variant image containers (.js-variant-alt)."""
        variants = []
        
        variant_containers = soup.find_all('a', class_='js-variant-alt')
        
        # Extract variant names from HTML
        upc_to_name = self._extract_variant_names_from_html(soup)
        
        # Extract variant images from HTML
        upc_to_image = self._extract_variant_images_from_html(soup)
        
        # Get product name for fallback
        product_name = self._extract_product_name_from_page(soup)
        
        for container in variant_containers:
            name = container.get('data-name', '')
            upcs_str = container.get('data-upcs', '')
            image = container.get('data-img-src', '')
            
            if name and upcs_str:
                upcs = [upc.strip() for upc in upcs_str.split(',') if upc.strip()]
                
                for upc in upcs:
                    # Dynamically determine what attribute this represents
                    attribute_name = self._infer_attribute_name_from_container(container, name)
                    attributes = {attribute_name: name}
                    
                    # Use real variant name from HTML, or generate as fallback
                    variant_name = upc_to_name.get(upc)
                    if not variant_name:
                        variant_name = self._generate_variant_name(product_name, attributes)
                    
                    # Detect variant-specific stock status
                    variant_stock_status = self._detect_variant_stock_status(soup, upc, attributes, stock_status)
                    
                    variant = {
                        'upc': upc,
                        'sku': sku,
                        'name': variant_name,
                        'price': base_price,
                        'product_id': product_id,
                        'stock_status': variant_stock_status,
                        'attributes': attributes,
                        'image': upc_to_image.get(upc, '')  # Always include image field, empty if not found
                    }
                    
                    variants.append(variant)
        
        return variants

    def _infer_attribute_name_from_container(self, container, name: str) -> str:
        """Infer what attribute type this container represents based on context."""
        name_lower = name.lower()
        
        # Check for common color patterns
        color_keywords = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple', 'gray', 'grey', 'brown', 'orange']
        if any(color in name_lower for color in color_keywords):
            return 'Color'
        
        # Check for size patterns
        import re
        if re.search(r'\d+|[xsml]+|small|medium|large', name_lower):
            return 'Size'
        
        # Check container classes for hints
        container_classes = ' '.join(container.get('class', []))
        if 'color' in container_classes.lower():
            return 'Color'
        elif 'size' in container_classes.lower():
            return 'Size'
        elif 'style' in container_classes.lower():
            return 'Style'
        
        # Default fallback - usually these containers represent color variations
        return 'Color'

    def _create_default_variant(self, soup: BeautifulSoup, product_id: str, stock_status: str, sku: str) -> Optional[Dict]:
        """Create a default variant when no variants are found."""
        # Extract base price
        price = self._extract_price_from_page(soup, soup)
        
        # Try to find UPC from multiple sources
        upc = None
        
        # 1. First try to extract from lclyPdpData
        lcly_data = self._extract_lcly_pdp_data(soup)
        if lcly_data:
            upc_prices = lcly_data.get('upc_prices', {})
            if upc_prices:
                # Use the first UPC from upc_prices
                upc = list(upc_prices.keys())[0]
        
        # 2. If no UPC found, try to find it in PowerReviews script
        if not upc:
            for script in soup.find_all('script'):
                if script.string and 'POWERREVIEWS.display.render' in script.string:
                    if '"upc":"' in script.string:
                        upc_start = script.string.find('"upc":"') + 7
                        upc_end = script.string.find('"', upc_start)
                        upc = script.string[upc_start:upc_end]
                        break
        
        # If still no UPC found, use product_id as last resort
        if not upc:
            upc = product_id
            
        # Get product name for the default variant
        product_name = self._extract_product_name_from_page(soup)
            
        # Create the default variant
        variant = {
            'upc': upc,
            'sku': sku,  # Use the product's SKU
            'name': product_name,  # Default variant uses the product name
            'price': price,
            'product_id': product_id,
            'stock_status': stock_status,
            'attributes': {},  # No attributes for default variant
            'image': ''  # No specific image for default variant
        }
        
        return variant

    def _detect_variant_stock_status(self, soup: BeautifulSoup, upc: str, attributes: Dict[str, str], default_stock_status: str) -> str:
        """
        Detect stock status for a specific variant based on UPC and attributes.
        If no specific variant stock is found, returns the general product stock status.
        """
        # Method 1: Look for variant-specific stock indicators with UPC
        variant_containers = soup.find_all('a', class_='js-variant-alt')
        for container in variant_containers:
            container_upcs = container.get('data-upcs', '')
            if upc in container_upcs:
                # Check if this container has stock indicators
                if 'is-in-stock' in container.get('class', []):
                    return 'in_stock'
                elif 'is-out-of-stock' in container.get('class', []):
                    return 'out_of_stock'
        
        # Method 2: Look for select options with stock status
        selects = soup.find_all('select')
        for select in selects:
            options = select.find_all('option')
            for option in options:
                option_upcs = option.get('data-upcs', '')
                if upc in option_upcs:
                    option_classes = option.get('class', [])
                    if 'out-of-stock' in option_classes or 'disabled' in option_classes:
                        return 'out_of_stock'
                    # If option exists and is not disabled, assume in stock
                    return 'in_stock'
        
        # Method 3: Check any attribute for disabled/out-of-stock options
        if attributes:
            disabled_options = soup.find_all('option', disabled=True)
            for option in disabled_options:
                option_text = option.get_text(strip=True).lower()
                # Check if any of our attribute values match disabled options
                for attr_value in attributes.values():
                    if attr_value and attr_value.lower() in option_text:
                        return 'out_of_stock'
        
        # Fallback: Use the general product stock status
        return default_stock_status

    def _generate_variant_name(self, product_name: str, attributes: Dict[str, str]) -> str:
        """
        Generate a descriptive name for a variant based on product name and attributes.
        
        Examples:
        - "Classic Clog - Black, M8"
        - "Classic Clog - Latte, M10"
        - "Nike Air Max - Red, Large"
        """
        if not attributes:
            return product_name
        
        # Create attribute string from all attributes
        attr_parts = []
        for attr_name, attr_value in attributes.items():
            if attr_value:  # Only include non-empty attributes
                attr_parts.append(attr_value)
        
        if attr_parts:
            return f"{product_name} - {', '.join(attr_parts)}"
        else:
            return product_name

    def _extract_product_name_from_page(self, soup: BeautifulSoup) -> str:
        """Extract the product name from the page for variant naming."""
        # Try to find product name in details container
        details_container = soup.find('div', class_='pdp-product-details')
        if details_container:
            name_elem = details_container.find('h3', class_='pdp-product-name')
            if name_elem:
                return name_elem.get_text(strip=True)
        
        # Fallback: try other common selectors
        name_selectors = [
            'h1.product-name',
            'h1',
            '.product-title',
            '.pdp-product-name'
        ]
        
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        return "Product"  # Ultimate fallback

    def _extract_variant_names_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract UPC -> variant name mappings from HTML JSON data.
        The HTML contains complete variant names like "Classic Clog (Black, M10W12)"
        """
        upc_to_name = {}
        
        # Look for JSON data containing variant names
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if script.string:
                content = script.string
                
                # Look for variant data with names
                if 'variants' in content and 'name' in content and 'upc' in content:
                    
                    # Try to extract JSON objects with upc and name
                    import re
                    
                    # Pattern to match {"upc":"...","name":"...","page_id_variant":"..."}
                    pattern = r'\{"upc":"([^"]+)","name":"([^"]+)","page_id_variant":"[^"]+"\}'
                    matches = re.findall(pattern, content)
                    
                    for upc, name in matches:
                        upc_to_name[upc] = name
                    
                    if matches:
                        break
        
        return upc_to_name

    def _extract_variant_images_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract UPC -> variant image mappings from HTML.
        Combines data from both JSON sources and direct HTML elements.
        """
        upc_to_image = {}
        
        # Method 1: Extract from .js-variant-alt containers (primary source)
        variant_containers = soup.find_all('a', class_='js-variant-alt')
        for container in variant_containers:
            upcs_str = container.get('data-upcs', '')
            image_url = container.get('data-img-src', '')
            
            if upcs_str and image_url:
                # Make image URL absolute
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    image_url = 'https://media.locally.com' + image_url
                
                # Parse UPCs and map each to the image
                upcs = [upc.strip() for upc in upcs_str.split(',') if upc.strip()]
                for upc in upcs:
                    upc_to_image[upc] = image_url
        
        # Method 2: Look for JSON data containing variant images (fallback)
        if not upc_to_image:
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string:
                    content = script.string
                    
                    # Look for variant data with images
                    if 'variants' in content and 'image' in content and 'upc' in content:
                        
                        # Try to extract JSON objects with upc and image
                        import re
                        
                        # Pattern to match {"upc":"...","image":"..."}
                        pattern = r'\{"upc":"([^"]+)","image":"([^"]+)"\}'
                        matches = re.findall(pattern, content)
                        
                        for upc, image in matches:
                            if image.startswith('//'):
                                image = 'https:' + image
                            elif image.startswith('/'):
                                image = 'https://media.locally.com' + image
                            upc_to_image[upc] = image
                        
                        if matches:
                            break
        
        return upc_to_image

    def _filter_variants_by_image(self, variants: List[Dict]) -> List[Dict]:
        """
        Filter variants based on image availability:
        - If only 1 variant: keep it regardless of image
        - If multiple variants: remove variants with empty images
        """
        if len(variants) <= 1:
            # Single variant or no variants: keep as is
            return variants
        
        # Multiple variants: filter out those with empty images
        filtered_variants = [v for v in variants if v.get('image', '').strip()]
        
        # If filtering removes all variants, keep the original list
        # (better to have variants without images than no variants at all)
        if not filtered_variants:
            return variants
        
        return filtered_variants 