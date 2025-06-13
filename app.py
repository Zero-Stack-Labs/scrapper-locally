from fastapi import FastAPI
from controllers.scraper_controller import ScraperController

app = FastAPI()

scraper_controller = ScraperController()
app.include_router(scraper_controller.router)
