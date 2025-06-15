from fastapi import FastAPI
from controllers.scraper_controller import ScraperController
from database import engine, Base
from utils.logging_config import get_logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = get_logger(__name__)

app = FastAPI()

health_thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="health-check")
scraper_controller = ScraperController()

def sync_health_check():
    return {"status": "healthy", "service": "scraper-locally"}

@app.get("/health")
async def health_check():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(health_thread_pool, sync_health_check)

@app.get("/api/scrapper-locally/health")
async def health_check():
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(health_thread_pool, sync_health_check)

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando aplicación de scraper")
    logger.info("✅ Aplicación iniciada correctamente")

app.include_router(scraper_controller.router)
