#!/usr/bin/env python3
"""
Initialize database tables from SQLAlchemy models
"""

import asyncio
import logging
from sqlalchemy import text

from src.core.database import engine, Base
from src.core.logging import setup_logging

# Import all models to ensure they're registered with Base
from src.models.lead import Lead, Assessment
from src.models.assessment_cost import AssessmentCost
from src.models.assessment_results import AssessmentResults
from src.models.pagespeed import (
    PageSpeedAnalysis, PageSpeedAudit, PageSpeedScreenshot,
    PageSpeedElement, PageSpeedEntity, PageSpeedOpportunity
)

setup_logging()
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database tables"""
    try:
        logger.info("Starting database initialization...")
        
        # Create all tables
        async with engine.begin() as conn:
            # First check if any tables exist
            result = await conn.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            logger.info(f"Found {table_count} existing tables")
            
            # Create all tables
            logger.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            
            # Verify tables were created
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            logger.info(f"Created {len(tables)} tables:")
            for table in tables:
                logger.info(f"  - {table[0]}")
            
            # Check for PageSpeed tables specifically
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'pagespeed%'
                ORDER BY table_name
            """))
            ps_tables = result.fetchall()
            logger.info(f"\nPageSpeed tables created: {len(ps_tables)}")
            for table in ps_tables:
                logger.info(f"  - {table[0]}")
            
            # Create alembic_version table if it doesn't exist
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))
            
            # Set the current version to the latest migration
            await conn.execute(text("DELETE FROM alembic_version"))
            await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('005')"))
            
            logger.info("\nDatabase initialization completed successfully!")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())