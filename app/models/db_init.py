# models/db_init.py

import os
import time
from typing import Optional

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .base import Base, logger
from .enums import SyncStatusEnum  # if needed

def setup_postgres_extensions(dbapi_connection, connection_record):
    """
    Set up PostgreSQL extensions (pgcrypto, pg_trgm, unaccent) on the raw DBAPI connection.
    """
    try:
        with dbapi_connection.cursor() as cursor:
            cursor.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
            cursor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
            cursor.execute('CREATE EXTENSION IF NOT EXISTS unaccent')
        dbapi_connection.commit()
    except Exception as e:
        logger.warning(f"Failed to create PostgreSQL extension: {e}")


# Register the event listener for "connect"
event.listen(Engine, "connect", setup_postgres_extensions)


def init_db(db_url: Optional[str] = None, echo: bool = False, max_retries: int = 3) -> sessionmaker:
    """
    Initializes the database engine and returns a session factory.
    Includes robust error handling and connection retry logic.
    """
    if not db_url:
        # Construct database URL from individual environment variables
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        user = os.environ.get("DB_USER", "postgres")
        password = os.environ.get("DB_PASSWORD", "postgres")
        dbname = os.environ.get("DB_NAME", "policypulse")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    
    engine = None
    attempt = 0

    while attempt < max_retries:
        try:
            engine = create_engine(
                db_url,
                echo=echo,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,
                max_overflow=20
            )
            # Test connection
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection established successfully")
            break
        except Exception as e:
            attempt += 1
            logger.warning(f"Database connection attempt {attempt} failed: {e}")
            if attempt >= max_retries:
                logger.error(f"Exceeded maximum retries ({max_retries}) for database connection.")
                raise

            wait_time = 2 ** attempt
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    # Create all tables
    try:
        Base.metadata.create_all(engine)
        logger.info("Database schema created or verified successfully")
    except Exception as e:
        logger.error(f"Failed to create database schema: {e}")
        raise

    return sessionmaker(bind=engine, expire_on_commit=False)
