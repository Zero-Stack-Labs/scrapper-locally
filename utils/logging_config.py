import logging
import os
from dotenv import load_dotenv

load_dotenv()

def setup_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ],
        force=True
    )

def get_logger(name: str):
    setup_logging()
    return logging.getLogger(name) 