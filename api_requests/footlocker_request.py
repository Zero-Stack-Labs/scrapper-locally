from pydantic import BaseModel, Field
from typing import Optional


class FootlockerScrapeRequest(BaseModel):
    query: str = Field(default="Nike", description="Search term for products")
    max_pages: int = Field(default=2, ge=1, le=100, description="Maximum number of pages to scrape")
    max_detail_workers: int = Field(default=3, ge=1, le=100, description="Maximum number of workers to get details")
    detail_delay: float = Field(default=1.0, ge=0.1, le=50.0, description="Delay between detail requests in seconds")
    api_delay: float = Field(default=2.0, ge=0.1, le=60.0, description="Delay between API pages in seconds")