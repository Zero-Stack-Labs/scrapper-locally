from fastapi import APIRouter, BackgroundTasks
from services.footlocker_service import FootlockerService
from api_requests.footlocker_request import FootlockerScrapeRequest
from utils.logging_config import get_logger
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid

logger = get_logger(__name__)

class FootlockerController:
    
    def __init__(self, scraper_thread_pool: ThreadPoolExecutor = None):
        self.router = APIRouter()
        self.scraper_thread_pool = scraper_thread_pool
        self.router.add_api_route("/api/scraper-footlocker/scrape", self.start_scrape, methods=["POST"])
    
    async def start_scrape(self, request: FootlockerScrapeRequest, background_tasks: BackgroundTasks):
        logger.info(f"Starting Footlocker scraping for query '{request.query}'")
        
        service = FootlockerService()
        task_id = str(uuid.uuid4())
        logger.info(f"Task created with ID: {task_id}")
        
        async def scraping_task_wrapper():
            try:
                if self.scraper_thread_pool:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        self.scraper_thread_pool,
                        service.scrape_footlocker_products,
                        request.query,
                        request.page_size,
                        request.sort,
                        request.save_every
                    )
                else:
                    service.scrape_footlocker_products(
                        query=request.query,
                        page_size=request.page_size,
                        sort=request.sort,
                        save_every=request.save_every
                    )
                logger.info(f"Footlocker scraping completed for task {task_id}")
            except Exception as e:
                logger.error(f"Error in background task {task_id}: {str(e)}", exc_info=True)
                raise
        
        background_tasks.add_task(scraping_task_wrapper)
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": "Footlocker scraping process initiated successfully",
        } 