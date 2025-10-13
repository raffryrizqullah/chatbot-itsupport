"""
Background scheduler for automatic cleanup of old PDF files.

This module manages scheduled tasks for cleaning up old files from R2 storage
based on the configured retention period.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.r2_storage import R2StorageService
from app.core.config import settings

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """
    Background scheduler for automatic file cleanup.

    Runs daily cleanup jobs to remove old PDF files from R2 storage
    based on the configured retention period.
    """

    def __init__(self) -> None:
        """Initialize the cleanup scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.r2_storage = R2StorageService()
        logger.info("Cleanup scheduler initialized")

    async def cleanup_old_files(self) -> None:
        """
        Execute cleanup of old files from R2 storage.

        This method is called by the scheduler and deletes files
        older than the configured retention period.
        """
        try:
            logger.info(
                f"Starting scheduled cleanup (retention: {settings.pdf_retention_days} days)"
            )
            deleted_count = self.r2_storage.delete_old_files()
            logger.info(
                f"Scheduled cleanup completed: {deleted_count} files deleted"
            )
        except Exception as e:
            msg = f"Scheduled cleanup failed: {str(e)}"
            logger.error(msg, exc_info=True)

    def start(self) -> None:
        """
        Start the cleanup scheduler.

        Schedules daily cleanup job at 2:00 AM UTC.
        """
        # Schedule cleanup job to run daily at 2:00 AM UTC
        self.scheduler.add_job(
            self.cleanup_old_files,
            trigger=CronTrigger(hour=2, minute=0),
            id="cleanup_old_files",
            name="Clean up old PDF files from R2 storage",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Cleanup scheduler started (runs daily at 2:00 AM UTC)")

    def shutdown(self) -> None:
        """
        Shutdown the cleanup scheduler.

        Stops all scheduled jobs and waits for them to complete.
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Cleanup scheduler stopped")


# Global scheduler instance
_scheduler_instance: CleanupScheduler = None


def get_scheduler() -> CleanupScheduler:
    """
    Get the global cleanup scheduler instance.

    Returns:
        CleanupScheduler instance.
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CleanupScheduler()
    return _scheduler_instance


async def start_scheduler() -> None:
    """Start the global cleanup scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global cleanup scheduler."""
    global _scheduler_instance
    if _scheduler_instance is not None:
        _scheduler_instance.shutdown()
        _scheduler_instance = None
