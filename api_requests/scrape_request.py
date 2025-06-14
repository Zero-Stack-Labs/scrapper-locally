from pydantic import BaseModel
from typing import List


class Location(BaseModel):
    zipcode: str
    lat: float
    lng: float


class ScrapeRequest(BaseModel):
    store_id: str
    store_name: str
    locations: List[Location]
    output_dir: str = "."
    page_delay: float = 5.0
    max_product_workers: int = 10
    max_page_workers: int = 3
    save_every: int = 5
    max_pages: int = None 