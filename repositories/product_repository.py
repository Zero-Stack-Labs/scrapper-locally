import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from models.product_db import ProductDB
from models.product import Product
from database import SessionLocal

logger = logging.getLogger(__name__)


class ProductRepository:
    
    def __init__(self):
        self.db_session = SessionLocal
    
    def upsert_product(self, product: Product, db: Optional[Session] = None) -> ProductDB:
        if db is None:
            db = self.db_session()
            should_close = True
        else:
            should_close = False
        
        try:
            product_data = self._product_to_db_dict(product)
            
            stmt = insert(ProductDB).values(**product_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['external_id', 'provider_id'],
                set_=dict(
                    name=stmt.excluded.name,
                    brand=stmt.excluded.brand,
                    url=stmt.excluded.url,
                    sku=stmt.excluded.sku,
                    images=stmt.excluded.images,
                    external_sell_price=stmt.excluded.external_sell_price,
                    currency=stmt.excluded.currency,
                    condition=stmt.excluded.condition,
                    description=stmt.excluded.description,
                    variants=stmt.excluded.variants,
                    variants_count=stmt.excluded.variants_count,
                    images_count=stmt.excluded.images_count,
                    page_number=stmt.excluded.page_number,
                    store_id=stmt.excluded.store_id,
                    lat=stmt.excluded.lat,
                    lng=stmt.excluded.lng,
                    zipcode=stmt.excluded.zipcode,
                    store_name=stmt.excluded.store_name
                )
            ).returning(ProductDB)
            
            result = db.execute(stmt)
            db.commit()
            
            product_db = result.fetchone()[0]
            logger.info(f"Producto upsert exitoso: {product.external_id}")
            
            return product_db
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error en upsert de producto {product.external_id}: {e}")
            raise e
        finally:
            if should_close:
                db.close()
    
    def _product_to_db_dict(self, product: Product) -> dict:
        return {
            'record_type': product.record_type,
            'provider_id': product.provider_id,
            'external_id': product.external_id,
            'name': product.name,
            'brand': product.brand,
            'url': product.url,
            'sku': product.sku,
            'images': product.images,
            'external_sell_price': product.external_sell_price,
            'currency': product.currency,
            'condition': product.condition,
            'description': product.description,
            'variants': product.variants,
            'variants_count': product.variants_count,
            'images_count': product.images_count,
            'page_number': product.page_number,
            'store_id': product.store_id,
            'lat': product.lat,
            'lng': product.lng,
            'zipcode': product.zipcode,
            'store_name': product.store_name
        } 