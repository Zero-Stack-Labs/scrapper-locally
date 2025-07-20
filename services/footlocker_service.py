import json
from typing import List, Dict, Any, Optional
from scrapers.footlocker.footlocker_scraper import FootlockerScraper
from repositories.product_repository import ProductRepository
from utils.logging_config import get_logger
from datetime import datetime
from utils.token_extractor import AntiDetectionExtractor


logger = get_logger(__name__)


class FootlockerService:
    def __init__(self):
        self.scraper = None
        self.product_repository = ProductRepository()
    
    def _get_dynamic_header(self, base_url: str, store_id: str) -> Optional[str]:
        token = None
        extractor = None
        try:
            logger.info(f"Iniciando extracción de token para {base_url} y tienda {store_id}...")
            
            target_url = f"{base_url}/category/brands/nike.htm"
            if store_id:
                target_url += f"?storeID={store_id}"
            
            # Use headless mode in containerized environments for resource efficiency
            import os
            is_containerized = os.environ.get('CHROME_BIN') is not None
            extractor = AntiDetectionExtractor(use_undetected=True, headless=is_containerized)
            token = extractor.get_token(target_url=target_url)

            if token:
                logger.info(f"✅ Token de seguridad obtenido con éxito para {base_url}")
            else:
                logger.warning(f"⚠️ No se pudo obtener el token de seguridad para {base_url}")

        except Exception as e:
            logger.error(f"Error al ejecutar AntiDetectionExtractor: {e}")
        finally:
            if extractor:
                extractor.close()
        
        return token

    def _get_scraper_config(self, site_type: str = 'main') -> Dict[str, Any]:
        base_url_map = {
            'kids': "https://www.kidsfootlocker.com",
            'main': "https://www.footlocker.com"
        }
        base_url = base_url_map.get(site_type, base_url_map['main'])

        with open('config/locations.json', 'r') as f:
            locations_config = json.load(f)
        
        location_data = locations_config.get(site_type)

        if not location_data:
            raise ValueError(f"No se encontró configuración de ubicación para site_type: {site_type}")
        
        store_id = location_data.get("store_id", "")
        x_kpsdk_ct = self._get_dynamic_header(base_url, store_id)

        config = {
            "base_url": base_url,
            "x_kpsdk_ct": x_kpsdk_ct
        }
        config.update(location_data)
        
        return config

    def scrape_footlocker_products(
        self,
        query: str = "Nike",
        max_pages: int = 2,
        max_detail_workers: int = 3,
        detail_delay: float = 1.0,
        api_delay: float = 2.0,
        site_type: str = 'main'
    ) -> Dict[str, Any]:
        
        config = self._get_scraper_config(site_type)
        self.scraper = FootlockerScraper(
            base_url=config['base_url'],
            x_kpsdk_ct=config['x_kpsdk_ct'],
            store_id=config['store_id'],
            latitude=config['latitude'],
            longitude=config['longitude'],
            zipcode=config['zipcode']
        )
        
        try:
            logger.info(f"Iniciando scraping de '{config['base_url']}' para query: '{query}'")
            
            products = self.scraper.scrape_products(
                query=query,
                max_pages=max_pages,
                max_detail_workers=max_detail_workers,
                detail_delay=detail_delay,
                api_delay=api_delay
            )
            
            if not products:
                logger.warning("No se encontraron productos")
                return {
                    "success": True,
                    "products_scraped": 0,
                    "query": query,
                    "message": "No se encontraron productos para la búsqueda especificada"
                }
            
            total_saved = self._save_products_to_db(products)
            
            logger.info(f"Scraping completado: {len(products)} productos obtenidos, {total_saved} guardados")
            
            return {
                "success": True,
                "products_scraped": len(products),
                "products_saved": total_saved,
                "query": query,
                "max_pages": max_pages,
                "message": f"Successfully scraped {len(products)} products from Footlocker, {total_saved} saved to database"
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

 