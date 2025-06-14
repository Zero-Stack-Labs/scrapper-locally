from typing import List, Dict, Any
from repositories.scraper_repository import ScraperRepository
from utils.stock_analyzer import StockAnalyzer
from pathlib import Path
import json
from datetime import datetime
import csv
from models.product import Product
from repositories.product_repository import ProductRepository
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ScraperService:

    def __init__(self, output_dir: str):
        self.repository = ScraperRepository(output_dir)
        self.analyzer = StockAnalyzer()
        self.output_dir = Path(output_dir)
        self.product_repository = ProductRepository()

    def process_single_store(self, store_config, scraper_params, store_id: str, store_name: str):
        logger.info(f"Processing store {store_id}")

        try:
            result = self.repository.scrape_single_store(
                store_id=store_id,
                zipcode=store_config["zipcode"],
                lat=store_config["lat"],
                lng=store_config["lng"],
                store_name=store_name,
                page_delay=scraper_params.get("page_delay", 2),
                max_product_workers=scraper_params.get("max_product_workers", 5),
                max_page_workers=scraper_params.get("max_page_workers", 3),
                save_every=scraper_params.get("save_every", 10),
                max_pages=scraper_params.get("max_pages", None)
            )

            logger.info(
                f"Scraping successful for store {store_id}: {result['products_scraped']} products")

            return {
                "success": True,
                "store_id": store_id,
                "zipcode": store_config["zipcode"],
                "products_scraped": result["products_scraped"],
                "products": result["products"],
                "message": f"Successfully scraped {result['products_scraped']} products"
            }

        except Exception as e:
            logger.error(f"Error processing store {store_id}: {e}", exc_info=True)
            return {
                "success": False,
                "store_id": store_id,
                "zipcode": store_config["zipcode"],
                "error": str(e),
                "message": f"Failed to scrape store: {str(e)}"
            }
