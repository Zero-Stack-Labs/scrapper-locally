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
        self.router.add_api_route("/api/scraper-footlocker/scrape-kids", self.start_scrape_kids, methods=["POST"])
    
    async def _run_scrape_task(self, request: FootlockerScrapeRequest, site_type: str):
        """Helper para ejecutar la tarea de scraping en segundo plano."""
        service = FootlockerService()
        task_id = str(uuid.uuid4())
        logger.info(f"Task '{task_id}' para site '{site_type}' con query '{request.query}'")

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
                        request.detail_delay,
                        request.api_delay,
                        site_type
                    )
                else:
                    result = service.scrape_footlocker_products(
                        query=request.query,
                        max_pages=request.max_pages,
                        max_detail_workers=request.max_detail_workers,
                        detail_delay=request.detail_delay,
                        api_delay=request.api_delay,
                        site_type=site_type
                    )
                
                logger.info(f"Scraping completado para task {task_id}: {result.get('message', 'Unknown result')}")
                
            except Exception as e:
                logger.error(f"Error en background task {task_id}: {str(e)}", exc_info=True)
                raise
            finally:
                service.scraper = None # Asegurar que se limpia
        
        return scraping_task_wrapper, task_id

    async def start_scrape(self, request: FootlockerScrapeRequest, background_tasks: BackgroundTasks):
        scraping_task, task_id = await self._run_scrape_task(request, site_type='main')
        background_tasks.add_task(scraping_task)
        
        return {
            "task_id": task_id,
            "status": "started",
            "query": request.query,
            "max_pages": request.max_pages,
            "message": "Footlocker scraping process initiated successfully",
        }
        
    async def start_scrape_kids(self, request: FootlockerScrapeRequest, background_tasks: BackgroundTasks):
        scraping_task, task_id = await self._run_scrape_task(request, site_type='kids')
        background_tasks.add_task(scraping_task)
        
        return {
            "task_id": task_id,
            "status": "started",
            "query": request.query,
            "max_pages": request.max_pages,
            "message": "Kids Footlocker scraping process initiated successfully",
        } 