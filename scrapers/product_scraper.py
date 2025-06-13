import json
import re
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from models.product import Product
from models.variant import Variant

logger = logging.getLogger(__name__)

class ProductScraper(BaseScraper):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_product_details_from_url(self, product_url: str) -> Optional[Product]:
        if not product_url:
            logger.warning("Empty product URL provided")
            return None
        
        logger.debug(f"Fetching product details from: {product_url}")
        
        response = self.make_request(product_url)
        
        if response is None:
            logger.warning(f"No response received for URL: {product_url}")
            return None
        
        if response.status_code == 200:
            logger.debug(f"Successfully fetched HTML (length: {len(response.text)})")
            return self.parse_product_details_page(response.text, product_url)
        else:
            logger.error(f"Error getting product {product_url}: {response.status_code}")
            return None
    
    def parse_product_details_page(self, html: str, product_url: str = "") -> Optional[Product]:
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('title')
        page_title = title.get_text(strip=True) if title else "No title found"
        logger.debug(f"Page title: {page_title}")
        
        pdp_wrapper = soup.find('div', id='pdp-wrapper')
        if not pdp_wrapper:
            logger.warning(f"❌ No 'pdp-wrapper' found for URL: {product_url}")
            
            divs_with_ids = soup.find_all('div', id=True)
            if divs_with_ids:
                div_ids = [div.get('id') for div in divs_with_ids[:10]]
                logger.debug(f"Available div IDs: {div_ids}")
            else:
                logger.debug("No divs with IDs found")
            
            error_indicators = [
                soup.find('h1', string=re.compile(r'404|not found|error', re.IGNORECASE)),
                soup.find(text=re.compile(r'page not found|404|error', re.IGNORECASE)),
                soup.find('div', class_=re.compile(r'error|404', re.IGNORECASE))
            ]
            
            if any(error_indicators):
                logger.warning(f"❌ Detected error page for URL: {product_url}")
                return None
            
            if 'loading' in html.lower() or 'redirect' in html.lower():
                logger.warning(f"❌ Page appears to be loading/redirecting for URL: {product_url}")
                return None
                
            return None
        
        logger.debug(f"✓ Found pdp-wrapper for URL: {product_url}")
        
        details_container = soup.find('div', class_='pdp-product-details')
        if not details_container:
            logger.debug("No 'pdp-product-details' found, using soup as container")
            details_container = soup
        
        external_id = pdp_wrapper.get('data-id') or details_container.get('data-switchlive-product-id')
        if not external_id:
            logger.warning(f"❌ No external_id found for URL: {product_url}")
            return None
        
        logger.debug(f"✓ Found external_id: {external_id}")
        
        brand_elem = details_container.find('h5', class_='pdp-brand')
        brand = brand_elem.get_text(strip=True) if brand_elem else ''
        
        name_elem = details_container.find('h3', class_='pdp-product-name')
        name = name_elem.get_text(strip=True) if name_elem else ''
        
        if not name:
            logger.warning(f"❌ No product name found for URL: {product_url}")
            return None
        
        logger.debug(f"✓ Found product: {name} (Brand: {brand})")
        
        stock_status = self._extract_stock_status_from_page(soup)
        
        product = Product(external_id, name, brand)
        
        product.url = self._extract_url_from_page(soup)
        product.sku = self._extract_sku_from_page(soup)
        product.currency = 'USD'
        
        price = self._extract_price_from_page(soup, details_container)
        product.external_sell_price = price
        
        description = self._extract_description_from_page(soup)
        product.description = description
        
        images = self._extract_images_from_page(soup)
        product.images = images
        
        variants = self._extract_variants_from_page(soup, external_id, stock_status, product.sku, images)
        
        product.variants = variants
        
        logger.debug(f"✅ Successfully parsed product {external_id}: {name} ({len(variants)} variants)")
        
        return product

    def _extract_url_from_page(self, soup: BeautifulSoup) -> str:
        canonical = soup.find('link', rel='canonical')
        if canonical and canonical.get('href'):
            return canonical['href']
        
        og_url = soup.find('meta', property='og:url')
        if og_url and og_url.get('content'):
            return og_url['content']
        
        return ''

    def _extract_sku_from_page(self, soup: BeautifulSoup) -> str:
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    sku = data.get('sku', '')
                    if sku:
                        return sku
            except:
                continue
        
        sku_meta = soup.find('meta', attrs={'name': 'product:retailer_item_id'})
        if sku_meta and sku_meta.get('content'):
            return sku_meta['content']
        
        return ''

    def _extract_price_from_page(self, soup: BeautifulSoup, details_container) -> float:
        price_elem = details_container.find('p', class_='pdp-price-amount')
        if price_elem:
            price = price_elem.get('data-bind-value')
            try:
                return float(price) if price else 0.0
            except (ValueError, TypeError):
                pass

        price_elem = soup.find('span', class_='js-variant-price')
        if price_elem:
            try:
                price_text = price_elem.get_text(strip=True)
                return float(price_text) if price_text else 0.0
            except (ValueError, TypeError):
                pass

        price_container = soup.find('span', class_='pdp-price')
        if price_container:
            price_min = price_container.get('data-price-min')
            try:
                return float(price_min) if price_min else 0.0
            except (ValueError, TypeError):
                pass

        return 0.0

    def _extract_description_from_page(self, soup: BeautifulSoup) -> str:
        description_parts = []
        
        info_content = soup.find('p', class_='pdp-information-content')
        if info_content:
            description_parts.append(info_content.get_text(strip=True))
        
        short_desc = soup.find('div', class_='pdp-short-description')
        if short_desc:
            description_parts.append(short_desc.get_text(strip=True))
        
        return "\n".join(description_parts)


    def _extract_images_from_page(self, soup: BeautifulSoup) -> List[str]:
        images = set()
        
        main_img = soup.find('img', class_='pdp-image')
        if main_img and main_img.get('src'):
            images.add(urljoin(self.base_url, main_img['src']))
        
        alt_images = soup.find_all('a', class_='js-variant-alt')
        for alt_img in alt_images:
            img_src = alt_img.get('data-img-src')
            if img_src:
                images.add(urljoin(self.base_url, img_src))
        
        all_imgs = soup.find_all('img')
        for img in all_imgs:
            src = img.get('src')
            if src and ('/spec-' in src or 'media.locally.com' in src):
                images.add(urljoin(self.base_url, src))
        
        return sorted(list(images))
    
    def _extract_variants_from_page(self, soup: BeautifulSoup, product_id: str, stock_status: str, sku: str, product_images: List[str] = None) -> List[Dict]:
        variants = self._extract_variants_from_javascript_data(soup, product_id, stock_status, sku)
        
        if not variants:
            variants = self._extract_variants_from_html_structure(soup, product_id, stock_status, sku)
        
        if not variants:
            default_variant = self._create_default_variant(soup, product_id, stock_status, sku, product_images)
            if default_variant:
                variants = [default_variant]
        
        variants = self._filter_variants_by_image(variants)
        
        return variants

    def _extract_variants_from_javascript_data(self, soup: BeautifulSoup, product_id: str, stock_status: str, sku: str) -> List[Dict]:
        lcly_data = self._extract_lcly_pdp_data(soup)
        if not lcly_data:
            return []
        
        all_upcs = lcly_data.get('all_upcs_carried', [])
        upc_prices = lcly_data.get('upc_prices', {})
        
        if not all_upcs and upc_prices:
            all_upcs = list(upc_prices.keys())
        
        if not all_upcs:
            return []
        
        attribute_mappings = self._extract_dynamic_attribute_mappings(soup)
        
        upc_to_name = self._extract_variant_names_from_html(soup)
        
        upc_to_image = self._extract_variant_images_from_html(soup)
        
        product_name = self._extract_product_name_from_page(soup)
        
        variants = []
        for upc in all_upcs:
            if isinstance(upc, str) and upc.strip():
                upc = upc.strip()
                
                price_info = upc_prices.get(upc, {})
                price = self._extract_price_from_upc_data(price_info)
                
                attributes = {}
                for attr_name, upc_mapping in attribute_mappings.items():
                    if upc in upc_mapping:
                        attributes[attr_name] = upc_mapping[upc]
                
                variant_name = upc_to_name.get(upc)
                if not variant_name:
                    variant_name = self._generate_variant_name(product_name, attributes)
                
                variant_stock_status = self._detect_variant_stock_status(soup, upc, attributes, stock_status)
                
                variant = {
                    'upc': upc,
                    'sku': sku,
                    'name': variant_name,
                    'price': price,
                    'product_id': product_id,
                    'stock_status': variant_stock_status,
                    'attributes': attributes,
                    'image': upc_to_image.get(upc, '')
                }
                
                variants.append(variant)
                
        
        return variants

    def _extract_variants_from_html_structure(self, soup: BeautifulSoup, product_id: str, stock_status: str, sku: str) -> List[Dict]:
        variants = []
        base_price = self._extract_price_from_page(soup, soup)
        
        variants = self._extract_from_dynamic_selectors(soup, product_id, base_price, stock_status, sku)
        
        if not variants:
            variants = self._extract_from_variant_containers(soup, product_id, base_price, stock_status, sku)
        
        return variants

    def _extract_dynamic_attribute_mappings(self, soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
        attribute_mappings = {}
        
        selects = soup.find_all('select')
        
        for select in selects:
            attr_name = self._determine_dynamic_attribute_name(select, soup)
            if not attr_name:
                continue
            
            
            upc_mapping = {}
            options = select.find_all('option')
            
            for option in options:
                option_name = option.get_text(strip=True)
                option_upcs = option.get('data-upcs', '')
                
                if option_name and option_upcs:
                    upcs = [upc.strip() for upc in option_upcs.split(',') if upc.strip()]
                    
                    for upc in upcs:
                        upc_mapping[upc] = option_name
            
            if upc_mapping:
                attribute_mappings[attr_name] = upc_mapping
        
        return attribute_mappings

    def _determine_dynamic_attribute_name(self, select, soup: BeautifulSoup) -> str:
        aria_label = select.get('aria-label', '')
        if aria_label:
            if aria_label.lower().startswith('choose '):
                return aria_label[7:].strip().title()
            elif 'choose' in aria_label.lower():
                parts = aria_label.lower().split()
                try:
                    choose_idx = parts.index('choose')
                    if choose_idx + 1 < len(parts):
                        return parts[choose_idx + 1].title()
                except ValueError:
                    pass
        
        select_classes = ' '.join(select.get('class', []))
        
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
        
        select_id = select.get('id', '')
        if select_id:
            label = soup.find('label', {'for': select_id})
            if label:
                label_text = label.get_text(strip=True)
                if label_text:
                    return label_text.replace(':', '').strip().title()
        
        options = select.find_all('option')
        if options:
            sample_options = [opt.get_text(strip=True).lower() for opt in options[:3]]
            
            color_keywords = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'grey', 'brown']
            if any(any(color in opt for color in color_keywords) for opt in sample_options):
                return 'Color'
            
            size_keywords = ['small', 'medium', 'large', 'xs', 'xl', 'm', 'l', 's']
            if any(any(size in opt for size in size_keywords) for opt in sample_options):
                return 'Size'
            
            import re
            size_patterns = [r'\d+', r'[XSML]+', r'\d+[WM]\d+']
            if any(any(re.search(pattern, opt) for pattern in size_patterns) for opt in sample_options):
                return 'Size'
        
        return None

    def _extract_price_from_upc_data(self, price_info: Dict) -> float:
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

    def _extract_lcly_pdp_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        script_tags = soup.find_all('script')
        
        
        for i, script in enumerate(script_tags):
            if script.string and 'lclyPdpData' in script.string:
                script_content = script.string
                
                patterns = [
                    r'var lclyPdpData = ({.*?});',
                    r'lclyPdpData = ({.*?});',
                    r'var lclyPdpData=({.*?});',
                    r'lclyPdpData=({.*?});',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, script_content, re.DOTALL)
                    if match:
                        try:
                            lcly_data = json.loads(match.group(1))
                            
                            all_upcs = lcly_data.get('all_upcs_carried', [])
                            upc_prices = lcly_data.get('upc_prices', {})
                            
                            if upc_prices:
                                sample_upcs = list(upc_prices.keys())[:3]
                            
                            return lcly_data
                        except json.JSONDecodeError as e:
                            continue
        
        
        js_with_content = [i for i, script in enumerate(script_tags) if script.string]
        
        for i, script in enumerate(script_tags):
            if script.string:
                content = script.string.lower()
                if any(keyword in content for keyword in ['upc', 'price', 'variant', 'pdp']):
                    snippet = script.string[:200] + "..." if len(script.string) > 200 else script.string
        
        return None

    def _extract_from_dynamic_selectors(self, soup: BeautifulSoup, product_id: str, base_price: float, stock_status: str, sku: str) -> List[Dict]:
        attribute_mappings = self._extract_dynamic_attribute_mappings(soup)
        
        if not attribute_mappings:
            return []
        
        all_upcs = set()
        for upc_mapping in attribute_mappings.values():
            all_upcs.update(upc_mapping.keys())
        
        
        upc_to_name = self._extract_variant_names_from_html(soup)
        
        upc_to_image = self._extract_variant_images_from_html(soup)
        
        product_name = self._extract_product_name_from_page(soup)
        
        variants = []
        for upc in all_upcs:
            attributes = {}
            for attr_name, upc_mapping in attribute_mappings.items():
                if upc in upc_mapping:
                    attributes[attr_name] = upc_mapping[upc]
            
            variant_name = upc_to_name.get(upc)
            if not variant_name:
                variant_name = self._generate_variant_name(product_name, attributes)
            
            variant_stock_status = self._detect_variant_stock_status(soup, upc, attributes, stock_status)
            
            variant = {
                'upc': upc,
                'sku': sku,
                'name': variant_name,
                'price': base_price,
                'product_id': product_id,
                'stock_status': variant_stock_status,
                'attributes': attributes,
                'image': upc_to_image.get(upc, '')
            }
            
            variants.append(variant)
            
        
        return variants

    def _extract_from_variant_containers(self, soup: BeautifulSoup, product_id: str, base_price: float, stock_status: str, sku: str) -> List[Dict]:
        variants = []
        
        variant_containers = soup.find_all('a', class_='js-variant-alt')
        
        upc_to_name = self._extract_variant_names_from_html(soup)
        
        upc_to_image = self._extract_variant_images_from_html(soup)
        
        product_name = self._extract_product_name_from_page(soup)
        
        for container in variant_containers:
            name = container.get('data-name', '')
            upcs_str = container.get('data-upcs', '')
            image = container.get('data-img-src', '')
            
            if name and upcs_str:
                upcs = [upc.strip() for upc in upcs_str.split(',') if upc.strip()]
                
                for upc in upcs:
                    attribute_name = self._infer_attribute_name_from_container(container, name)
                    attributes = {attribute_name: name}
                    
                    variant_name = upc_to_name.get(upc)
                    if not variant_name:
                        variant_name = self._generate_variant_name(product_name, attributes)
                    
                    variant_stock_status = self._detect_variant_stock_status(soup, upc, attributes, stock_status)
                    
                    variant = {
                        'upc': upc,
                        'sku': sku,
                        'name': variant_name,
                        'price': base_price,
                        'product_id': product_id,
                        'stock_status': variant_stock_status,
                        'attributes': attributes,
                        'image': upc_to_image.get(upc, '')
                    }
                    
                    variants.append(variant)
        
        return variants

    def _infer_attribute_name_from_container(self, container, name: str) -> str:
        name_lower = name.lower()
        
        color_keywords = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple', 'gray', 'grey', 'brown', 'orange']
        if any(color in name_lower for color in color_keywords):
            return 'Color'
        
        import re
        if re.search(r'\d+|[xsml]+|small|medium|large', name_lower):
            return 'Size'
        
        container_classes = ' '.join(container.get('class', []))
        if 'color' in container_classes.lower():
            return 'Color'
        elif 'size' in container_classes.lower():
            return 'Size'
        elif 'style' in container_classes.lower():
            return 'Style'
        
        return 'Color'

    def _create_default_variant(self, soup: BeautifulSoup, product_id: str, stock_status: str, sku: str, product_images: List[str] = None) -> Optional[Dict]:
        price = self._extract_price_from_page(soup, soup)
        
        upc = None
        
        lcly_data = self._extract_lcly_pdp_data(soup)
        if lcly_data:
            upc_prices = lcly_data.get('upc_prices', {})
            if upc_prices:
                upc = list(upc_prices.keys())[0]
        
        if not upc:
            for script in soup.find_all('script'):
                if script.string and 'POWERREVIEWS.display.render' in script.string:
                    if '"upc":"' in script.string:
                        upc_start = script.string.find('"upc":"') + 7
                        upc_end = script.string.find('"', upc_start)
                        upc = script.string[upc_start:upc_end]
                        break
        
        if not upc:
            upc = product_id
            
        product_name = self._extract_product_name_from_page(soup)
        
        main_image = product_images[0] if product_images and len(product_images) > 0 else ''
            
        variant = {
            'upc': upc,
            'sku': sku,
            'name': product_name,
            'price': price,
            'product_id': product_id,
            'stock_status': stock_status,
            'attributes': {},
            'image': main_image
        }
        
        return variant


    def get_product_details_batch(self, product_urls: List[str], max_workers: int = 5) -> List[Product]:
        import concurrent.futures
        
        detailed_products = []
        failed_urls = []
        
        logger.info(f"Getting details for {len(product_urls)} products (max {max_workers} workers)...")
        
        if product_urls:
            logger.debug(f"Sample URLs: {product_urls[:3]}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.get_product_details_from_url, url): url
                for url in product_urls
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    product = future.result()
                    if product:
                        detailed_products.append(product)
                        logger.debug(f"✅ Successfully processed: {url}")
                    else:
                        failed_urls.append(url)
                        logger.warning(f"❌ Failed to process: {url}")
                except Exception as exc:
                    failed_urls.append(url)
                    logger.error(f'❌ Exception processing product {url}: {exc}')
        
        success_rate = len(detailed_products) / len(product_urls) * 100 if product_urls else 0
        logger.info(f"Successfully scraped {len(detailed_products)}/{len(product_urls)} products ({success_rate:.1f}%)")
        
        if failed_urls:
            logger.warning(f"Failed URLs sample: {failed_urls[:3]}")
        
        return detailed_products

    def _extract_stock_status_from_page(self, soup: BeautifulSoup) -> str:
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
        
        stock_indicators = soup.find_all(text=True)
        for text in stock_indicators:
            text_lower = text.strip().lower()
            if 'in stock' in text_lower:
                return 'in_stock'
            elif 'out of stock' in text_lower:
                return 'out_of_stock'
        
        return 'unknown'

    def _detect_variant_stock_status(self, soup: BeautifulSoup, upc: str, attributes: Dict[str, str], default_stock_status: str) -> str:
        variant_containers = soup.find_all('a', class_='js-variant-alt')
        for container in variant_containers:
            container_upcs = container.get('data-upcs', '')
            if upc in container_upcs:
                if 'is-in-stock' in container.get('class', []):
                    return 'in_stock'
                elif 'is-out-of-stock' in container.get('class', []):
                    return 'out_of_stock'
        
        selects = soup.find_all('select')
        for select in selects:
            options = select.find_all('option')
            for option in options:
                option_upcs = option.get('data-upcs', '')
                if upc in option_upcs:
                    option_classes = option.get('class', [])
                    if 'out-of-stock' in option_classes or 'disabled' in option_classes:
                        return 'out_of_stock'
                    return 'in_stock'
        
        if attributes:
            disabled_options = soup.find_all('option', disabled=True)
            for option in disabled_options:
                option_text = option.get_text(strip=True).lower()
                for attr_value in attributes.values():
                    if attr_value and attr_value.lower() in option_text:
                        return 'out_of_stock'
        
        return default_stock_status 

    def _generate_variant_name(self, product_name: str, attributes: Dict[str, str]) -> str:
        if not attributes:
            return product_name
        
        attr_parts = []
        for attr_name, attr_value in attributes.items():
            if attr_value:
                attr_parts.append(attr_value)
        
        if attr_parts:
            return f"{product_name} - {', '.join(attr_parts)}"
        else:
            return product_name

    def _extract_product_name_from_page(self, soup: BeautifulSoup) -> str:
        details_container = soup.find('div', class_='pdp-product-details')
        if details_container:
            name_elem = details_container.find('h3', class_='pdp-product-name')
            if name_elem:
                return name_elem.get_text(strip=True)
        
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
        
        return "Product"

    def _extract_variant_names_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        upc_to_name = {}
        
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if script.string:
                content = script.string
                
                if 'variants' in content and 'name' in content and 'upc' in content:
                    
                    import re
                    
                    pattern = r'\{"upc":"([^"]+)","name":"([^"]+)","page_id_variant":"[^"]+"\}'
                    matches = re.findall(pattern, content)
                    
                    for upc, name in matches:
                        upc_to_name[upc] = name
                    
                    if matches:
                        break
        
        return upc_to_name 

    def _extract_variant_images_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        upc_to_image = {}
        
        variant_containers = soup.find_all('a', class_='js-variant-alt')
        for container in variant_containers:
            upcs_str = container.get('data-upcs', '')
            image_url = container.get('data-img-src', '')
            
            if upcs_str and image_url:
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                elif image_url.startswith('/'):
                    image_url = 'https://media.locally.com' + image_url
                
                upcs = [upc.strip() for upc in upcs_str.split(',') if upc.strip()]
                for upc in upcs:
                    upc_to_image[upc] = image_url
        
        if not upc_to_image:
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string:
                    content = script.string
                    
                    if 'variants' in content and 'image' in content and 'upc' in content:
                        
                        import re
                        
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
        if len(variants) <= 1:
            return variants
        
        filtered_variants = [v for v in variants if v.get('image', '').strip()]
        
        if not filtered_variants:
            return variants
        
        return filtered_variants 