from sqlalchemy import Column, String, Float, Integer, Text, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base


class ProductDB(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_type = Column(String(50), default="product")
    provider_id = Column(String(255), default="www.locally.com")
    external_id = Column(String(255), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    brand = Column(String(255), default="")
    url = Column(Text, default="")
    sku = Column(String(255), default="")
    images = Column(JSON, default=list)
    external_sell_price = Column(Float, default=0.0)
    currency = Column(String(10), default="")
    condition = Column(String(100), default="")
    description = Column(Text, default="")
    variants = Column(JSON, default=list)
    variants_count = Column(Integer, default=0)
    images_count = Column(Integer, default=0)
    page_number = Column(Integer, nullable=True)
    store_id = Column(String(255), default="")
    lat = Column(Float, default=0.0)
    lng = Column(Float, default=0.0)
    zipcode = Column(String(20), default="")
    store_name = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False) 