from typing import List, Dict, Any
from repositories.scraper_repository import ScraperRepository
from analyzers.stock_analyzer import StockAnalyzer
from pathlib import Path
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ScraperService:
    
    def __init__(self, output_dir: str):
        self.repository = ScraperRepository(output_dir)
        self.analyzer = StockAnalyzer()
        self.output_dir = Path(output_dir)
    
    def scrape_multiple_stores(self, store_configurations, scraper_params):
        """
        Scraper múltiples stores con configuraciones específicas.
        """
        results = []
        all_products = []
        
        for config in store_configurations:
            result = self.process_single_store(config, scraper_params)
            
            if result["success"]:
                all_products.extend(result["products"])
            
            results.append(result)
        
        analysis_result = self.generate_analysis(all_products, store_configurations)
        
        return {
            "results": results,
            "total_products": len(all_products),
            "analysis_generated": analysis_result["success"]
        }
    
    def process_single_store(self, store_config, scraper_params):
        """
        Procesa una sola tienda y retorna el resultado.
        """
        logger.info(f"Processing store {store_config['store_id']}")
        
        try:
            result = self.repository.scrape_single_store(
                store_id=store_config["store_id"],
                zipcode=store_config["zipcode"],
                lat=store_config["lat"],
                lng=store_config["lng"],
                store_name=store_config.get("store_name", ""),
                page_delay=scraper_params.get("page_delay", 2),
                max_product_workers=scraper_params.get("max_product_workers", 5),
                save_every=scraper_params.get("save_every", 10)
            )
            
            logger.info(f"Scraping successful for store {store_config['store_id']}: {result['products_scraped']} products")
            
            return {
                "success": True,
                "store_id": store_config["store_id"],
                "zipcode": store_config["zipcode"],
                "products_scraped": result["products_scraped"],
                "products": result["products"],
                "message": f"Successfully scraped {result['products_scraped']} products"
            }
            
        except Exception as e:
            logger.error(f"Error processing store {store_config['store_id']}: {e}", exc_info=True)
            return {
                "success": False,
                "store_id": store_config["store_id"],
                "zipcode": store_config["zipcode"],
                "error": str(e),
                "message": f"Failed to scrape store: {str(e)}"
            }
    
    def generate_analysis(self, all_products, store_configurations):
        """
        Genera análisis de stock y lo guarda en archivo.
        """
        try:
            if not all_products:
                return {
                    "success": False,
                    "message": "No products available for analysis"
                }
            
            stock_analysis = self.analyzer.analyze_stock_patterns(all_products)
            availability_by_store = self.analyzer.analyze_availability_by_store(all_products)
            
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "total_products_analyzed": len(all_products),
                "stores_analyzed": len(store_configurations),
                "stock_analysis": stock_analysis,
                "availability_by_store": availability_by_store,
                "store_configurations": [
                    {
                        "store_id": config["store_id"],
                        "zipcode": config["zipcode"]
                    }
                    for config in store_configurations
                ]
            }
            
            analysis_file = self.output_dir / f"stock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "message": f"Analysis saved to {analysis_file}",
                "analysis_file": str(analysis_file)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate analysis: {str(e)}"
            } 