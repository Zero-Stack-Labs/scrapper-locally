import csv
from pathlib import Path
from typing import List, Dict
from utils.logging_config import get_logger

logger = get_logger(__name__)

def read_store_csv(csv_name: str) -> List[Dict[str, str]]:
    csv_path = Path("config") / f"{csv_name}.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    stores = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                stores.append({
                    'store_id': row['storeId'],
                    'store_name': row['storeName'],
                    'zipcode': row['postalCode'],
                    'lat': float(row['latitude']),
                    'lng': float(row['longitude'])
                })
        
        logger.info(f"Successfully loaded {len(stores)} stores from {csv_path}")
        return stores
        
    except Exception as e:
        logger.error(f"Error reading CSV file {csv_path}: {str(e)}")
        raise