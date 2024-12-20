"""
This file imports all the ORM entity classes in the `database.entities` package.

Why is this important?
=======================
SQLAlchemy uses a declarative base (`Base`) to manage metadata and register ORM models. 
For `Base.metadata.create_all(bind=engine)` to work correctly and create the corresponding tables,
all ORM models must be imported and registered with `Base`.

Without importing the models here, `Base.metadata` will not contain the table definitions, 
resulting in no tables being created in the database during initialization.

Resolution:
===========
By explicitly importing all ORM models in this file, we ensure they are registered with `Base`, 
allowing `create_tables` in the `Database` class to function as expected.

If new ORM models are added in the future, make sure to import them here.

Imported Models:
================
- Project
- Microservice
- MicroserviceSession
- TokenUsage
- RAGAnalytics
"""

from utils.logs.logging_utils import logger

try:
    from .microservice_sessions import MicroserviceSession
    from .microservices import Microservice
    from .projects import Project
    from .rag_analytics import RAGAnalytics
    from .token_usage import TokenUsage 
except ImportError as e:
    logger.error(f"Failed to import one or more ORM models: {e}")
    raise
