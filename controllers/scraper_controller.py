from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from managers.scraper_manager import ScraperManager
from api_requests.scrape_request import ScrapeRequest, Location
from api_requests.csv_scrape_request import CsvScrapeRequest
from services.csv_scraper_service import CsvScraperService
from utils.logging_config import get_logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = get_logger(__name__)

class ScraperController:
    
    def __init__(self, scraper_thread_pool: ThreadPoolExecutor = None):
        self.router = APIRouter()
        self.scraper_thread_pool = scraper_thread_pool
        self.csv_scraper_service = CsvScraperService(scraper_thread_pool)
        self.router.add_api_route("/api/scrapper-locally/scrape", self.start_scrape, methods=["POST"])
        self.router.add_api_route("/api/scrapper-locally/scrape-csv", self.start_csv_scrape, methods=["POST"])
    
    async def start_scrape(self, request: ScrapeRequest, background_tasks: BackgroundTasks):
        logger.info(f"Starting scraping for {len(request.locations)} stores")
        
        output_path = Path(request.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        manager = ScraperManager(request.output_dir)
        
        scraper_params = {
            "page_delay": request.page_delay,
            "max_product_workers": request.max_product_workers,
            "max_page_workers": request.max_page_workers,
            "save_every": request.save_every,
            "max_pages": request.max_pages
        }
        
        locations = [location.dict() for location in request.locations]
        task_id = manager.start_scraping_task(locations, scraper_params, request.store_id, request.store_name)
        logger.info(f"Task created with ID: {task_id}")
        
        async def scraping_task_wrapper():
            try:
                if self.scraper_thread_pool:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        self.scraper_thread_pool,
                        manager.perform_scraping_task,
                        task_id, locations, scraper_params, request.store_id, request.store_name
                    )
                else:
                    manager.perform_scraping_task(task_id, locations, scraper_params, request.store_id, request.store_name)
                logger.info(f"Scraping completed for task {task_id}")
            except Exception as e:
                logger.error(f"Error in background task {task_id}: {str(e)}", exc_info=True)
                raise
        
        background_tasks.add_task(scraping_task_wrapper)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": "Scraping process initiated successfully",
        }
    
    async def start_csv_scrape(self, request: CsvScrapeRequest, background_tasks: BackgroundTasks):
        logger.info(f"Starting CSV-based scraping for {request.csv_name}.csv")
        
        scraper_params = {
            "page_delay": request.page_delay,
            "max_product_workers": request.max_product_workers,
            "max_page_workers": request.max_page_workers,
            "save_every": request.save_every,
            "max_pages": request.max_pages
        }
        
        task_id = self.csv_scraper_service.start_csv_scraping_task(
            request.csv_name, 
            request.output_dir, 
            scraper_params
        )
        
        background_tasks.add_task(
            self.csv_scraper_service.process_csv_stores,
            task_id,
            request.csv_name,
            request.output_dir,
            scraper_params
        )
        
        return {
            "task_id": task_id,
            "csv_name": request.csv_name,
            "status": "started",
            "message": f"CSV-based scraping process initiated for {request.csv_name}.csv",
        }