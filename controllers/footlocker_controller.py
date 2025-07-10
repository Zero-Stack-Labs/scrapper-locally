from fastapi import APIRouter, BackgroundTasks
from api_requests.footlocker_request import FootlockerScrapeRequest
from services.footlocker_service import FootlockerService
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
                    result = await loop.run_in_executor(
                        self.scraper_thread_pool,
                        service.scrape_footlocker_products,
                        request.query,
                        request.max_pages,
                        request.max_detail_workers,
                        request.detail_delay
                    )
                else:
                    result = service.scrape_footlocker_products(
                        query=request.query,
                        max_pages=request.max_pages,
                        max_detail_workers=request.max_detail_workers,
                        detail_delay=request.detail_delay
                    )
                
                logger.info(f"Footlocker scraping completed for task {task_id}: {result.get('message', 'Unknown result')}")
                
            except Exception as e:
                logger.error(f"Error in background task {task_id}: {str(e)}", exc_info=True)
                raise
            finally:
                service.scraper = None
        
        background_tasks.add_task(scraping_task_wrapper)
        
        return {
            "task_id": task_id,
            "status": "started",
            "query": request.query,
            "max_pages": request.max_pages,
            "message": "Footlocker scraping process initiated successfully",
        } 