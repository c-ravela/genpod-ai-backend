from sqlalchemy.orm import DeclarativeBase

from utils.logs.logging_utils import logger

logger.debug("Starting the setup of the declarative base for SQLAlchemy models.")

try:
    class Base(DeclarativeBase):
        """
        Base class for SQLAlchemy models, providing dynamic string representation for instances.
        """
        logger.debug("Defining the Base class for SQLAlchemy models.")

        def __repr__(self):
            """
            Dynamically creates a string representation of the instance.
            """
            attributes = ", ".join(
                f"{key}={value!r}" for key, value in self.__dict__.items() if not key.startswith("_")
            )
            return f"<{self.__class__.__name__}({attributes})>"

    logger.info("Declarative base for SQLAlchemy models defined successfully.")
except Exception as e:
    logger.exception("Failed to define the declarative base for SQLAlchemy models.")
    raise
finally:
    logger.debug("Setup process for the declarative base is complete.")
