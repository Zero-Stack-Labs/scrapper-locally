from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from managers.scraper_manager import ScraperManager
from api_requests.scrape_request import ScrapeRequest
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ScraperController:
    
    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route("/scrape", self.start_scrape, methods=["POST"])
    
    async def start_scrape(self, request: ScrapeRequest, background_tasks: BackgroundTasks):
        logger.info(f"Starting scraping for {len(request.locations)} stores")
        
        output_path = Path(request.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        manager = ScraperManager(request.output_dir)
        
        scraper_params = {
            "page_delay": request.page_delay,
            "max_product_workers": request.max_product_workers,
            "save_every": request.save_every,
            "max_pages": request.max_pages
        }
        
        locations = [location.dict() for location in request.locations]
        task_id = manager.start_scraping_task(locations, scraper_params, request.store_id, request.store_name)
        logger.info(f"Task created with ID: {task_id}")
        
        async def scraping_task_wrapper():
            try:
                await manager.perform_scraping_task(task_id, locations, scraper_params, request.store_id, request.store_name)
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