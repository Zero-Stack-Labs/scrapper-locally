from fastapi import FastAPI
from controllers.scraper_controller import ScraperController
from database import engine, Base
from utils.logging_config import get_logger

logger = get_logger(__name__)

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/scrapper-locally/health")
async def health_check():
    return {"status": "healthy complete"}

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Iniciando aplicación de scraper")
    logger.info("✅ Aplicación iniciada correctamente")

scraper_controller = ScraperController()
app.include_router(scraper_controller.router)
