from typing import List, Dict, Any
from scrapers.footlocker_scraper import FootlockerScraper
from models.product import Product
from repositories.product_repository import ProductRepository
from utils.logging_config import get_logger
import json
from datetime import datetime

logger = get_logger(__name__)


class FootlockerService:

    def __init__(self):
        self.scraper = FootlockerScraper()
        self.product_repository = ProductRepository()

    def scrape_footlocker_products(self, 
                                   query: str = "Nike",
                                   page_size: int = 250,
                                   sort: str = "relevance",
                                   save_every: int = 10) -> Dict[str, Any]:
        logger.info(f"Iniciando scraping de Footlocker para query '{query}'")
        
        try:
            all_products = []
            current_page = 0
            total_saved = 0
            
            while True:
                logger.info(f"Scrapeando página {current_page}...")
                
                products = self.scraper.scrape_products(
                    query=query,
                    current_page=current_page,
                    page_size=page_size,
                    sort=sort
                )
                
                if not products:
                    logger.info(f"No se encontraron productos en la página {current_page}. Terminando scraping.")
                    break
                
                for product in products:
                    product.created_at = datetime.now()
                    product.updated_at = datetime.now()
                
                all_products.extend(products)
                current_page += 1
                
                if len(all_products) >= save_every:
                    saved_count = self._save_products_batch(all_products[:save_every])
                    total_saved += saved_count
                    all_products = all_products[save_every:]
                    logger.info(f"Guardado progreso: {total_saved} productos guardados hasta ahora")
            
            if all_products:
                saved_count = self._save_products_batch(all_products)
                total_saved += saved_count
            
            logger.info(f"Scraping de Footlocker completado. Total: {total_saved} productos")
            
            return {
                "success": True,
                "products_scraped": total_saved,
                "pages_scraped": current_page,
                "query": query,
                "message": f"Successfully scraped {total_saved} products from Footlocker"
            }
            
        except Exception as e:
            logger.error(f"Error en scraping de Footlocker: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to scrape Footlocker: {str(e)}"
            }

    def _save_products_batch(self, products: List[Product]) -> int:
        try:
            saved_to_db = 0
            for product in products:
                try:
                    self.product_repository.upsert_product(product)
                    saved_to_db += 1
                except Exception as db_error:
                    logger.warning(f"Error guardando producto {product.external_id} en BD: {db_error}")
            
            logger.info(f"Guardados {saved_to_db} productos en base de datos")
            return len(products)
            
        except Exception as e:
            logger.error(f"Error guardando lote de productos: {e}")
            return 0

 