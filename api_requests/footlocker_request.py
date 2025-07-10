from pydantic import BaseModel, Field
from typing import Optional


class FootlockerScrapeRequest(BaseModel):
    query: str = Field(default="Nike", description="Término de búsqueda para productos")
    max_pages: int = Field(default=2, ge=1, le=10, description="Número máximo de páginas a scrapear")
    max_detail_workers: int = Field(default=3, ge=1, le=10, description="Número máximo de workers para obtener detalles")
    detail_delay: float = Field(default=1.0, ge=0.1, le=5.0, description="Delay entre requests de detalles en segundos") 