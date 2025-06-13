from typing import Dict, List, Any
import uuid
import threading
from datetime import datetime
from services.scraper_service import ScraperService
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class ScraperManager:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.service = ScraperService(output_dir)
        self._lock = threading.Lock()

    def start_scraping_task(self, store_configurations: List[Dict[str, Any]], scraper_params: Dict[str, Any]) -> str:
        task_id = str(uuid.uuid4())
        
        with self._lock:
            self.tasks[task_id] = {
                "id": task_id,
                "status": "pending",
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "progress": 0,
                "total_stores": len(store_configurations),
                "completed_stores": 0,
                "results_summary": [],
                "results_file": None,
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

    async def perform_scraping_task(self, task_id: str, store_configurations: List[Dict[str, Any]], scraper_params: Dict[str, Any]):
        self.update_task_status(task_id, "processing")
        
        total_stores = len(store_configurations)
        all_products = []
        
        for i, store_config in enumerate(store_configurations):
            try:
                result = self.service.process_single_store(store_config, scraper_params)
                all_products.extend(result.get("products", []))
                
                with self._lock:
                    self.tasks[task_id]["completed_stores"] = i + 1
                    self.tasks[task_id]["progress"] = ((i + 1) / total_stores) * 100
                    self.tasks[task_id]["results_summary"].append(result)

            except Exception as e:
                logger.error(f"Error processing store {store_config.get('store_id')} for task {task_id}: {e}", exc_info=True)
                with self._lock:
                    self.tasks[task_id]["results_summary"].append({
                        "success": False,
                        "store_id": store_config.get("store_id"),
                        "error": str(e)
                    })

        results_file = self.save_final_results(task_id, all_products)
        
        self.update_task_status(
            task_id,
            "completed",
            end_time=datetime.now().isoformat(),
            progress=100,
            results_file=results_file
        )
    
    def save_final_results(self, task_id: str, products: List[Dict]) -> str:
        results_dir = self.output_dir / task_id
        results_dir.mkdir(parents=True, exist_ok=True)
        results_file = results_dir / "scraped_products.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
            
        return str(results_file)

    def task_exists(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self.tasks

    def is_task_completed(self, task_id: str) -> bool:
        with self._lock:
            task = self.tasks.get(task_id)
            return task and task["status"] == "completed"

    def get_task_results(self, task_id: str) -> Dict[str, Any]:
        with self._lock:
            task = self.tasks.get(task_id, {})
            results_file = task.get("results_file")
            
            if results_file and Path(results_file).exists():
                with open(results_file, 'r', encoding='utf-8') as f:
                    products = json.load(f)
                return {"task_info": task, "products": products}
            
            return {"task_info": task, "products": []}
    
    def scrape_multiple_stores(self, store_configurations: List[Dict[str, Any]], scraper_params: Dict[str, Any]) -> Dict[str, Any]:
        return self.service.scrape_multiple_stores(store_configurations, scraper_params) 