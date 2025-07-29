import json
import os
from typing import List, Dict, Any, Optional
from scrapers.footlocker.footlocker_scraper import FootlockerScraper
from repositories.product_repository import ProductRepository
from utils.logging_config import get_logger
from utils.footlocker_stock_analyzer import FootlockerStockAnalyzer
from datetime import datetime
from utils.token_extractor import AntiDetectionExtractor


logger = get_logger(__name__)


class FootlockerService:
    def __init__(self):
        self.scraper = None
        self.product_repository = ProductRepository()
        self.stock_analyzer = FootlockerStockAnalyzer()

    def _get_dynamic_header(self, base_url: str, store_id: str) -> Optional[str]:
        token = None
        extractor = None
        
        # Check if we're in container environment and have ScraperAPI available
        is_container = os.path.exists('/.dockerenv') or os.environ.get('KUBERNETES_SERVICE_HOST')
        scraperapi_key = os.environ.get('SCRAPERAPI_KEY')
        
        try:
            logger.info(f"Starting token extraction for {base_url} and store {store_id}...")
            
            target_url = f"{base_url}/category/brands/nike.htm"
            if store_id:
                target_url += f"?storeID={store_id}"

            if is_container and scraperapi_key:
                # Use ScraperAPI for token extraction in container environment
                logger.info("🌐 Using ScraperAPI for token extraction in container environment")
                token = self._extract_token_via_scraperapi(target_url, scraperapi_key)
            else:
                # Use local browser extraction
                logger.info("🏠 Using local browser for token extraction")
                extractor = AntiDetectionExtractor(use_undetected=True, headless=is_container)
                token = extractor.get_token(target_url=target_url)

            if token:
                logger.info(f"✅ Security token obtained successfully for {base_url}")
            else:
                logger.warning(f"⚠️ Could not obtain security token for {base_url}")

        except Exception as e:
            logger.error(f"Error running token extraction: {e}")
            logger.error(f"Error type: {type(e).__name__}")
        finally:
            if extractor:
                extractor.close()
        
        return token
    
    def _extract_token_via_scraperapi(self, target_url: str, api_key: str) -> Optional[str]:
        """Extract token using ScraperAPI with multiple strategies"""
        import requests
        import re
        import time
        
        strategies = [
            {
                'name': 'Ultra Premium + Render',
                'params': {
                    'api_key': api_key,
                    'url': target_url,
                    'ultra_premium': 'true',
                    'render': 'true',
                    'wait': 5,
                    'country_code': 'us',
                    'device_type': 'desktop',
                    'session_number': 1,
                }
            },
            {
                'name': 'Ultra Premium + Custom Headers',
                'params': {
                    'api_key': api_key,
                    'url': target_url,
                    'ultra_premium': 'true',
                    'render': 'false',
                    'country_code': 'us',
                    'premium': 'true',
                    'session_number': 2,
                    'custom_header_User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                    'custom_header_Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'custom_header_Accept-Language': 'en-US,en;q=0.5',
                }
            },
            {
                'name': 'Regular Premium Fallback',
                'params': {
                    'api_key': api_key,
                    'url': target_url,
                    'premium': 'true',
                    'render': 'false',
                    'country_code': 'us',
                    'session_number': 3,
                }
            }
        ]
        
        api_url = "http://api.scraperapi.com"
        
        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"🔧 Trying ScraperAPI strategy {i+1}/3: {strategy['name']}")
                
                response = requests.get(api_url, params=strategy['params'], timeout=60)
                
                if response.status_code == 200:
                    page_content = response.text
                    logger.info(f"✅ ScraperAPI request successful with {strategy['name']}")
                    
                    # Look for the token in page content
                    token = self._extract_token_from_content(page_content)
                    if token:
                        logger.info(f"✅ Token extracted successfully: {token[:50]}...")
                        return token
                    else:
                        logger.warning(f"⚠️ No token found in content from {strategy['name']}")
                        
                elif response.status_code == 403:
                    logger.warning(f"🚫 Strategy {strategy['name']} blocked (403), trying next...")
                    if i < len(strategies) - 1:
                        time.sleep(2)  # Brief delay before next strategy
                        continue
                else:
                    logger.error(f"❌ Strategy {strategy['name']} failed: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Strategy {strategy['name']} error: {e}")
                continue
        
        # If all ScraperAPI strategies fail, return your working token as fallback
        logger.warning("⚠️ All ScraperAPI strategies failed, using fallback token")
        fallback_token = "02OzXAYIPvLByDPH2P3vfkpM3yR7EFQ18HCMnYRcYhx3G3L4zBnfleWC8onXFkuMJoENiwOdptW7aK9YAQzDe51nwgfBIhNgoi2mq6GbnWtqmcPPqIQws80EOFypoPT1sSHcno27STFq2CkemFzsKYhtPgBy3chQyV3CfX4H54"
        logger.info(f"🔄 Using fallback token: {fallback_token[:50]}...")
        return fallback_token
    
    def _extract_token_from_content(self, page_content: str) -> Optional[str]:
        """Extract token from page content using various patterns"""
        import re
        
        # Multiple patterns to find the token
        token_patterns = [
            r'x-kpsdk-ct["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'kpsdk["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'token["\']?\s*[:=]\s*["\']([A-Za-z0-9]{200,})["\']',
            r'"x-kpsdk-ct"\s*:\s*"([^"]+)"',
            r"'x-kpsdk-ct'\s*:\s*'([^']+)'",
            r'x-kpsdk-ct=([A-Za-z0-9]{200,})',
        ]
        
        for pattern in token_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                token = matches[0]
                # Validate token format (should be long alphanumeric string)
                if len(token) > 100 and token.replace('_', '').replace('-', '').isalnum():
                    return token
        
        return None

    def _get_locations_config(self, site_type: str = 'main') -> List[Dict[str, Any]]:
        with open('config/locations.json', 'r') as f:
            locations_config = json.load(f)

        locations = locations_config.get(site_type, [])

        if not locations:
            raise ValueError(f"No se encontró configuración de ubicaciones para site_type: {site_type}")

        return locations

    def _get_base_url(self, site_type: str) -> str:
        base_url_map = {
            'kids': "https://www.kidsfootlocker.com",
            'main': "https://www.footlocker.com",
            'champs': "https://www.champssports.com"
        }
        return base_url_map.get(site_type, base_url_map['main'])

    def scrape_footlocker_products(
        self,
        query: str = "Nike",
        max_pages: int = 2,
        max_detail_workers: int = 3,
        detail_delay: float = 1.0,
        api_delay: float = 2.0,
        site_type: str = 'main'
    ) -> Dict[str, Any]:
        
        try:
            base_url = self._get_base_url(site_type)
            locations = self._get_locations_config(site_type)

            logger.info(f"Iniciando scraping de '{base_url}' para {len(locations)} ubicaciones")

            logger.info("🔐 Extrayendo token de seguridad una sola vez para todo el sitio...")
            first_location = locations[0]
            x_kpsdk_ct = self._get_dynamic_header(base_url, first_location['store_id'])
            #x_kpsdk_ct = "0ar5J7VAK650hneH1OLuHDeJfW2LLPkNn6Y79gg22BfA6lkugljxvSrHnoGao9phY5q8bOvZyH1aZjo5ZQqqBsD4SaE9CSs0SCEB2lOnuk5bKcN5goOzXrcAcph8MNkCKnAUWfZQZXr2p3wxgJl1pIieoOgbrN5VDX2IGzA"

            if not x_kpsdk_ct:
                logger.error("❌ No se pudo obtener el token de seguridad. Abortando scraping.")
                return {
                    "success": False,
                    "error": "Failed to extract security token",
                    "message": "No se pudo obtener el token de seguridad requerido"
                }

            logger.info(f"✅ Token obtenido exitosamente. Procesando {len(locations)} ubicaciones...")

            all_products = []
            all_zipcodes = []

            for i, location in enumerate(locations, 1):
                logger.info(f"Procesando ubicación {i}/{len(locations)}: store_id={location['store_id']}, zipcode={location['zipcode']}")

                self.scraper = FootlockerScraper(
                    base_url=base_url,
                    x_kpsdk_ct=x_kpsdk_ct,
                    store_id=location['store_id'],
                    latitude=location['latitude'],
                    longitude=location['longitude'],
                    zipcode=location['zipcode']
                )

                try:
                    products = self.scraper.scrape_products(
                        query=query,
                        max_pages=max_pages,
                        max_detail_workers=max_detail_workers,
                        detail_delay=detail_delay,
                        api_delay=api_delay
                    )

                    if products:
                        all_products.extend(products)
                        all_zipcodes.append(location['zipcode'])
                        logger.info(f"✅ Ubicación {location['zipcode']}: {len(products)} productos obtenidos")
                    else:
                        logger.warning(f"⚠️ Ubicación {location['zipcode']}: No se encontraron productos")

                finally:
                    if self.scraper:
                        self.scraper.close()
                        self.scraper = None
            
            if not all_products:
                logger.warning("No se encontraron productos en ninguna ubicación")
                return {
                    "success": True,
                    "products_scraped": 0,
                    "products_unified": 0,
                    "query": query,
                    "message": "No se encontraron productos en ninguna ubicación"
                }
            
            logger.info(f"Productos totales obtenidos: {len(all_products)} de {len(locations)} ubicaciones")

            unified_products = self.stock_analyzer.analyze_multi_location_stock(all_products, all_zipcodes)
            
            total_saved = self._save_products_to_db(unified_products)

            logger.info(f"Scraping completed: {len(all_products)} products obtained, {len(unified_products)} unificados, {total_saved} saved")
            
            return {
                "success": True,
                "products_scraped": len(all_products),
                "products_unified": len(unified_products),
                "products_saved": total_saved,
                "locations_processed": len(locations),
                "query": query,
                "max_pages": max_pages,
                "message": f"Successfully scraped {len(all_products)} products from {len(locations)} locations, unified to {len(unified_products)} products, {total_saved} saved to database"
            }
            
        except Exception as e:
            logger.error(f"Error en FootlockerService: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to scrape Footlocker: {str(e)}"
            }
        finally:
            if self.scraper:
                self.scraper.close()
                self.scraper = None
    
    def _save_products_to_db(self, products: List) -> int:
        try:
            saved_count = 0
            for product in products:
                try:
                    product.created_at = datetime.now()
                    product.updated_at = datetime.now()
                    
                    self.product_repository.upsert_product(product)
                    saved_count += 1
                    logger.debug(f"✅ Producto guardado: {product.external_id}")
                    
                except Exception as db_error:
                    logger.warning(f"❌ Error guardando producto {product.external_id}: {db_error}")
            
            logger.info(f"Guardados {saved_count}/{len(products)} productos en base de datos")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error general guardando productos: {e}")
            return 0

 