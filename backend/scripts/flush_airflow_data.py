"""Flush old Airflow capsule data from the database.

This script removes Airflow DAG and task data that was incorrectly stored as capsules
before the orchestration metamodel refactor.
"""

import asyncio
import logging

from sqlalchemy import delete, select

from src.database import async_session_maker
from src.models.capsule import Capsule
from src.models.lineage import CapsuleLineage
from src.models.source_system import SourceSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def flush_airflow_capsules():
    """Remove Airflow capsules and related data from the database."""
    async with async_session_maker() as session:
        try:
            # Find Airflow capsules (old format)
            result = await session.execute(
                select(Capsule).where(
                    Capsule.capsule_type.in_(["airflow_dag", "airflow_task"])
                )
            )
            airflow_capsules = result.scalars().all()

            if not airflow_capsules:
                logger.info("No Airflow capsules found to flush")
                return

            logger.info(f"Found {len(airflow_capsules)} Airflow capsules to remove")

            # Get URNs for edge cleanup
            capsule_urns = {c.urn for c in airflow_capsules}

            # Delete edges involving these capsules
            result = await session.execute(
                delete(CapsuleLineage).where(
                    (CapsuleLineage.source_urn.in_(capsule_urns))
                    | (CapsuleLineage.target_urn.in_(capsule_urns))
                )
            )
            edges_deleted = result.rowcount
            logger.info(f"Deleted {edges_deleted} edges involving Airflow capsules")

            # Delete the capsules (this will cascade to columns and other related data)
            result = await session.execute(
                delete(Capsule).where(
                    Capsule.capsule_type.in_(["airflow_dag", "airflow_task"])
                )
            )
            capsules_deleted = result.rowcount
            logger.info(f"Deleted {capsules_deleted} Airflow capsules")

            # Find Airflow source systems
            result = await session.execute(
                select(SourceSystem).where(SourceSystem.source_type == "airflow")
            )
            airflow_sources = result.scalars().all()

            if airflow_sources:
                logger.info(f"Found {len(airflow_sources)} Airflow source systems")
                for source in airflow_sources:
                    logger.info(f"  - {source.name} (id: {source.id})")
                    # Note: We don't delete source systems as they may be referenced
                    # by the new pipeline data

            await session.commit()
            logger.info("✅ Successfully flushed old Airflow capsule data")

        except Exception as e:
            await session.rollback()
            logger.exception(f"❌ Error flushing Airflow data: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(flush_airflow_capsules())
