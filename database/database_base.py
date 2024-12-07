from sqlalchemy.orm import DeclarativeBase

from utils.logs.logging_utils import logger

logger.debug("Starting the setup of the declarative base for SQLAlchemy models.")

try:
    class Base(DeclarativeBase):
        logger.debug("Defining the Base class for SQLAlchemy models.")
    
    logger.info("Declarative base for SQLAlchemy models defined successfully.")
except Exception as e:
    logger.exception("Failed to define the declarative base for SQLAlchemy models.")
    raise
finally:
    logger.debug("Setup process for the declarative base is complete.")
