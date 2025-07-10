from pydantic import BaseModel


class FootlockerScrapeRequest(BaseModel):
    query: str = "Nike"
    page_size: int = 250
    sort: str = "relevance"
    save_every: int = 10 