import json
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
        try:
            logger.info(f"Starting token extraction for {base_url} and store {store_id}...")
            
            target_url = f"{base_url}/category/brands/nike.htm"
            if store_id:
                target_url += f"?storeID={store_id}"

            extractor = AntiDetectionExtractor(use_undetected=True, headless=False)
            token = extractor.get_token(target_url=target_url)

            if token:
                logger.info(f"✅ Security token obtained successfully for {base_url}")
            else:
                logger.warning(f"⚠️ Could not obtain security token for {base_url}")

        except Exception as e:
            logger.error(f"Error running AntiDetectionExtractor: {e}")
        finally:
            if extractor:
                extractor.close()
        
        return token

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

 