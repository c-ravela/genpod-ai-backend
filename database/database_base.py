from sqlalchemy.orm import declarative_base

from utils.logs.logging_utils import logger

logger.debug("Initializing declarative base for SQLAlchemy models.")
try:
    Base = declarative_base()
    logger.info("Declarative base initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing declarative base: {e}")
    raise
finally:
    logger.debug("Declarative base setup process completed.")
