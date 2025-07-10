from pydantic import BaseModel, Field
from typing import Optional


class FootlockerScrapeRequest(BaseModel):
    query: str = Field(default="Nike", description="Término de búsqueda para productos")
    max_pages: int = Field(default=2, ge=1, le=100, description="Número máximo de páginas a scrapear")
    max_detail_workers: int = Field(default=3, ge=1, le=100, description="Número máximo de workers para obtener detalles")
    detail_delay: float = Field(default=1.0, ge=0.1, le=50.0, description="Delay entre requests de detalles en segundos")
    api_delay: float = Field(default=2.0, ge=0.1, le=60.0, description="Delay entre páginas de API en segundos")