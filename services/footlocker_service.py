from typing import List, Dict, Any
from scrapers.footlocker.footlocker_scraper import FootlockerScraper
from repositories.product_repository import ProductRepository
from utils.logging_config import get_logger
from datetime import datetime

logger = get_logger(__name__)


class FootlockerService:
    def __init__(self):
        self.scraper = None
        self.product_repository = ProductRepository()
        
    def scrape_footlocker_products(
        self,
        query: str = "Nike",
        max_pages: int = 2,
        max_detail_workers: int = 3,
        detail_delay: float = 1.0
    ) -> Dict[str, Any]:
        
        self.scraper = FootlockerScraper()
        
        try:
            logger.info(f"Iniciando scraping de Footlocker para query: '{query}'")
            
            products = self.scraper.scrape_products(
                query=query,
                max_pages=max_pages,
                max_detail_workers=max_detail_workers,
                detail_delay=detail_delay
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

 