from typing import Dict, Any, List
from pathlib import Path
from managers.scraper_manager import ScraperManager
from api_requests.scrape_request import Location
from utils.csv_utils import read_store_csv
from utils.logging_config import get_logger
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

logger = get_logger(__name__)

class CsvScraperService:
    
    def __init__(self, scraper_thread_pool: ThreadPoolExecutor = None):
        self.scraper_thread_pool = scraper_thread_pool
    
    def start_csv_scraping_task(self, csv_name: str, output_dir: str, scraper_params: Dict[str, Any]) -> str:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        manager = ScraperManager(output_dir)
        task_id = f"csv_{csv_name}_{str(uuid.uuid4())}"
        
        logger.info(f"Starting CSV-based scraping task {task_id} for {csv_name}.csv")
        
        return task_id
    
    async def process_csv_stores(self, task_id: str, csv_name: str, output_dir: str, scraper_params: Dict[str, Any]):
        try:
            stores = read_store_csv(csv_name)
            logger.info(f"Processing {len(stores)} stores from {csv_name}.csv")
            
            manager = ScraperManager(output_dir)
            
            for store in stores:
                location = Location(
                    zipcode=store['zipcode'],
                    lat=store['lat'],
                    lng=store['lng']
                )
                locations = [location.dict()]
                
                if self.scraper_thread_pool:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        self.scraper_thread_pool,
                        manager.perform_scraping_task,
                        task_id, locations, scraper_params, store['store_id'], store['store_name']
                    )
                else:
                    manager.perform_scraping_task(task_id, locations, scraper_params, store['store_id'], store['store_name'])
                
                logger.info(f"Completed scraping for store {store['store_id']}: {store['store_name']}")
            
            logger.info(f"CSV scraping completed for all {len(stores)} stores from {csv_name}")
            
        except FileNotFoundError as e:
            logger.error(f"CSV file not found: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in CSV background task {task_id}: {str(e)}", exc_info=True)
            raise