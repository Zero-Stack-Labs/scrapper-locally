from fastapi import APIRouter, HTTPException, BackgroundTasks
from pathlib import Path
from managers.scraper_manager import ScraperManager
from api_requests.scrape_request import ScrapeRequest
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperController:
    
    def __init__(self):
        self.router = APIRouter()
        self.router.add_api_route("/scrape", self.start_scrape, methods=["POST"])
        self.router.add_api_route("/scrape/status/{task_id}", self.get_scrape_status, methods=["GET"])
        self.router.add_api_route("/scrape/results/{task_id}", self.get_scrape_results, methods=["GET"])
        self.router.add_api_route("/scrape/debug", self.debug_scrape, methods=["POST"])
    
    async def start_scrape(self, request: ScrapeRequest, background_tasks: BackgroundTasks):
        logger.info(f"Starting scraping for {len(request.store_configurations)} stores")
        
        output_path = Path(request.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        manager = ScraperManager(request.output_dir)
        
        scraper_params = {
            "page_delay": request.page_delay,
            "max_product_workers": request.max_product_workers,
            "save_every": request.save_every
        }
        
        store_configs = [config.dict() for config in request.store_configurations]
        task_id = manager.start_scraping_task(store_configs, scraper_params)
        logger.info(f"Task created with ID: {task_id}")
        
        async def scraping_task_wrapper():
            try:
                await manager.perform_scraping_task(task_id, store_configs, scraper_params)
                logger.info(f"Scraping completed for task {task_id}")
            except Exception as e:
                logger.error(f"Error in background task {task_id}: {str(e)}", exc_info=True)
                raise
        
        background_tasks.add_task(scraping_task_wrapper)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": "Scraping process initiated successfully",
            "estimated_time": f"{len(request.store_configurations) * 30} seconds (approximately)",
            "endpoints": {
                "status": f"/scrape/status/{task_id}",
                "results": f"/scrape/results/{task_id}"
            }
        }
    
    async def get_scrape_status(self, task_id: str):
        manager = ScraperManager(".")
        
        if not manager.task_exists(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        return manager.get_task_status(task_id)
    
    async def get_scrape_results(self, task_id: str):
        manager = ScraperManager(".")
        
        if not manager.task_exists(task_id):
            raise HTTPException(status_code=404, detail="Task not found")
        
        if not manager.is_task_completed(task_id):
            task_status = manager.get_task_status(task_id)
            raise HTTPException(
                status_code=202, 
                detail={
                    "message": "Task still processing",
                    "status": task_status["status"],
                    "progress": task_status["progress"]
                }
            )
        
        return manager.get_task_results(task_id)
    
    async def debug_scrape(self, request: ScrapeRequest):
        """
        Debug endpoint that executes scraping synchronously for real-time logs
        """
        logger.info("DEBUG: Starting synchronous scraping")
        
        try:
            output_path = Path(request.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            manager = ScraperManager(request.output_dir)
            
            scraper_params = {
                "page_delay": request.page_delay,
                "max_product_workers": request.max_product_workers,
                "save_every": request.save_every
            }
            
            store_configs = [config.dict() for config in request.store_configurations]
            
            task_id = manager.start_scraping_task(store_configs, scraper_params)
            
            await manager.perform_scraping_task(task_id, store_configs, scraper_params)
            
            results = manager.get_task_results(task_id)
            
            return {
                "debug_mode": True,
                "task_id": task_id,
                "status": "completed_sync",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in debug_scrape: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Debug scraping failed: {str(e)}")
 