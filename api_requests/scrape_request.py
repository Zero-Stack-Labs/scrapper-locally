from pydantic import BaseModel
from typing import List


class StoreConfig(BaseModel):
    zipcode: str
    lat: float
    lng: float
    store_id: str
    store_name: str


class ScrapeRequest(BaseModel):
    store_configurations: List[StoreConfig]
    output_dir: str = "."
    page_delay: float = 5.0
    max_product_workers: int = 10
    save_every: int = 5
    max_pages: int = None 