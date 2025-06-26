from typing import Dict, List, Any
import uuid
import threading
from datetime import datetime
import requests
from services.scraper_service import ScraperService
from pathlib import Path
import json
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ScraperManager:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.service = ScraperService(output_dir)
        self._lock = threading.Lock()

    def start_scraping_task(self, locations: List[Dict[str, Any]], scraper_params: Dict[str, Any], store_id: str = "", store_name: str = "") -> str:
        task_id = str(uuid.uuid4())
        
        with self._lock:
            self.tasks[task_id] = {
                "id": task_id,
                "status": "pending",
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "progress": 0,
                "total_stores": len(locations),
                "completed_stores": 0,
                "results_summary": [],
            }
        
        return task_id

    def update_task_status(self, task_id: str, status: str, **kwargs):
        with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = status
                self.tasks[task_id].update(kwargs)

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        with self._lock:
            return self.tasks.get(task_id, {"status": "not_found"})

    def sync_with_walmart_service(self, store_name: str):
        try:
            sync_url = "http://walmart-server-service.microservices:3000/sync"
            payload = {"store_filter": store_name}
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(sync_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully synced with walmart service for store: {store_name}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to sync with walmart service for store {store_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during sync for store {store_name}: {e}")
            return False

    def perform_scraping_task(self, task_id: str, locations: List[Dict[str, Any]], scraper_params: Dict[str, Any], store_id: str = "", store_name: str = ""):
        self.update_task_status(task_id, "processing")
        
        total_stores = len(locations)
        all_products = []
        
        for i, store_config in enumerate(locations):
            try:
                result = self.service.process_single_store(store_config, scraper_params, store_id, store_name)
                all_products.extend(result.get("products", []))
                
                with self._lock:
                    self.tasks[task_id]["completed_stores"] = i + 1
                    self.tasks[task_id]["progress"] = ((i + 1) / total_stores) * 100
                    self.tasks[task_id]["results_summary"].append(result)

            except Exception as e:
                logger.error(f"Error processing store {store_id} for task {task_id}: {e}", exc_info=True)
                with self._lock:
                    self.tasks[task_id]["results_summary"].append({
                        "success": False,
                        "store_id": store_id,
                        "error": str(e)
                    })
        
        if all_products:
            logger.info(f"Generando análisis de stock para {len(all_products)} productos...")
            self.generate_stock_analysis(all_products, locations)
        
        self.update_task_status(
            task_id,
            "completed",
            end_time=datetime.now().isoformat(),
            progress=100,
        )
        
        if store_name:
            logger.info(f"Initiating sync with walmart service for store: {store_name}")
            self.sync_with_walmart_service(store_name)
    
    def generate_stock_analysis(self, all_products: List[Dict], locations: List[Dict]):
        try:
            from utils.stock_analyzer import StockAnalyzer
            analyzer = StockAnalyzer(str(self.output_dir))
            analyzer.generate_stock_analysis_files(all_products, locations)
            logger.info("✅ Análisis de stock y upsert completados")
        except Exception as e:
            logger.error(f"❌ Error en análisis de stock: {e}", exc_info=True)
