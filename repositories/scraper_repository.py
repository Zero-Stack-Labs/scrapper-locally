from typing import List, Dict, Any
from scrapers.locally_scraper import LocallyScraper
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ScraperRepository:
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
    
    def scrape_single_store(self, store_id: str, zipcode: str, lat: float, lng: float,
                           store_name: str = "",
                           page_delay: float = 2.0, 
                           max_product_workers: int = 5, 
                           save_every: int = 10,
                           max_pages: int = None) -> Dict[str, Any]:
        logger.info(f"Starting scraping for store {store_id}")
        
        store_config = {
            "store_id": store_id,
            "zipcode": zipcode,
            "lat": lat,
            "lng": lng,
            "store_name": store_name
        }
        
        try:
            scraper = LocallyScraper(
                output_dir=self.output_dir,
                store_config=store_config,
            )
            
            products = scraper.scrape_all_products_with_delays(
                page_delay=page_delay,
                max_product_workers=max_product_workers,
                save_progress_every=save_every,
                max_pages=max_pages
            )
            
            logger.info(f"Products obtained: {len(products)}")
            
            for product in products:
                product['location_zipcode'] = zipcode
                product['store_id'] = store_id
            
            logger.info(f"Scraping completed successfully for {store_id}")
            
            return {
                "products_scraped": len(products),
                "products": products,
                "store_id": store_id,
                "zipcode": zipcode
            }
            
        except Exception as e:
            logger.error(f"Error in scrape_single_store: {e}", exc_info=True)
            raise