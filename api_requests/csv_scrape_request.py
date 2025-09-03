from pydantic import BaseModel

class CsvScrapeRequest(BaseModel):
    csv_name: str
    output_dir: str = "."
    page_delay: float = 15.0
    max_product_workers: int = 30
    max_page_workers: int = 5
    save_every: int = 5
    max_pages: int = None