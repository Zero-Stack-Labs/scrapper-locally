from typing import List, Dict, Any
from scrapers.locally_scraper import LocallyScraper
import logging

logger = logging.getLogger(__name__)

class ScraperRepository:
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
    
    def scrape_single_store(self, store_id: str, zipcode: str, lat: float, lng: float,
                           store_name: str = "",
                           page_delay: float = 2.0, 
                           max_product_workers: int = 5, 
                           save_every: int = 10) -> Dict[str, Any]:
        logger.info(f"Starting scraping for store {store_id}")
        
        store_config = {
            "store_id": store_id,
            "zipcode": zipcode,
            "lat": lat,
            "lng": lng,
            "store_name": store_name
        }
        
        filename_suffix = f"{store_id}_{zipcode}"
        
        try:
            scraper = LocallyScraper(
                output_dir=self.output_dir,
                store_config=store_config,
                filename_suffix=filename_suffix
            )
            
            products = scraper.scrape_all_products_with_delays(
                page_delay=page_delay,
                max_product_workers=max_product_workers,
                save_progress_every=save_every
            )
            
            logger.info(f"Products obtained: {len(products)}")
            
            for product in products:
                product['location_zipcode'] = zipcode
                product['store_id'] = store_id
            
            scraper.save_results(products)
            
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
    
    def scrape_store_products(self, 
                             store_config: Dict[str, Any], 
                             filename_suffix: str,
                             scraper_params: Dict[str, Any]) -> List[Dict]:
        scraper = LocallyScraper(
            output_dir=self.output_dir,
            store_config=store_config,
            filename_suffix=filename_suffix
        )
        
        products = scraper.scrape_all_products_with_delays(
            page_delay=scraper_params.get('page_delay', 5.0),
            max_product_workers=scraper_params.get('max_product_workers', 10),
            save_progress_every=scraper_params.get('save_every', 5)
        )
        
        scraper.save_results(products)
        return products
    
    def generate_stock_analysis(self, 
                               all_products: List[Dict], 
                               store_configurations: List[Dict]) -> bool:
        try:
            from utils.stock_analyzer import StockAnalyzer
            analyzer = StockAnalyzer(self.output_dir)
            analyzer.generate_stock_analysis_files(all_products, store_configurations)
            return True
        except Exception as e:
            logger.error(f"Error generating stock analysis: {e}")
            return False 