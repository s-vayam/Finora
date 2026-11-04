import argparse
import datetime
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database import SessionLocal
from app.services.fx_provider_service import FxProviderService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [FxScheduler] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("finora.fx_scheduler")

LOCK_FILE = backend_dir / "data" / "fx_scheduler.lock"


class FxScheduler:
    def __init__(self, interval_minutes: Optional[int] = None, dry_run: bool = False):
        self.interval_seconds = (interval_minutes or settings.FX_REFRESH_INTERVAL_MINUTES) * 60
        self.dry_run = dry_run
        self.running = False
        self.service = FxProviderService()
        self._lock_acquired = False

    def acquire_lock(self) -> bool:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
            fd = os.open(str(LOCK_FILE), flags)
            with os.fdopen(fd, "w") as f:
                f.write(str(os.getpid()))
            self._lock_acquired = True
            return True
        except FileExistsError:
            logger.error(f"Scheduler lock file already exists at {LOCK_FILE}. Another instance is running.")
            return False
        except Exception as e:
            logger.error(f"Failed to acquire scheduler lock: {e}")
            return False

    def release_lock(self):
        if self._lock_acquired and LOCK_FILE.exists():
            try:
                LOCK_FILE.unlink()
                self._lock_acquired = False
            except Exception as e:
                logger.warning(f"Failed to release lock file: {e}")

    def execute_job(self) -> bool:
        logger.info("Executing scheduled FX fetch job...")
        db = SessionLocal()
        try:
            quota = self.service.get_quota_status(db)
            logger.info(f"Quota status: {quota.requests_today} today, {quota.requests_this_month}/{quota.monthly_budget} this month")
            if quota.is_budget_exceeded:
                logger.warning(f"Monthly request budget ({quota.monthly_budget}) exhausted! Skipping external fetch.")
                return False

            if self.dry_run:
                logger.info("[Dry Run] Would fetch live rates from provider.")
                return True

            result = self.service.fetch_latest_rates(db)
            if result.success:
                logger.info(f"Fetch success: {result.message} -> Rates: {result.rates_fetched}")
                return True
            else:
                logger.error(f"Fetch failed: {result.message} (Status: {result.status})")
                return False
        except Exception as e:
            logger.error(f"Unexpected error during FX fetch job: {e}", exc_info=True)
            return False
        finally:
            db.close()

    def run_once(self) -> bool:
        logger.info("Starting single execution (--once)...")
        return self.execute_job()

    def run_loop(self):
        if not self.acquire_lock():
            logger.error("Could not start scheduler loop: lock acquisition failed.")
            return

        self.running = True
        logger.info(f"FX Scheduler daemon started. Polling interval: {self.interval_seconds // 60} minutes.")

        def shutdown_handler(signum, frame):
            logger.info(f"Received termination signal ({signum}). Initiating graceful shutdown...")
            self.running = False

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        try:
            while self.running:
                start_time = time.time()
                self.execute_job()

                # Sleep in 1-second increments to allow responsive shutdown
                sleep_duration = self.interval_seconds
                logger.info(f"Next fetch in {sleep_duration // 60} minutes. Heartbeat active.")
                
                elapsed = 0
                while self.running and elapsed < sleep_duration:
                    time.sleep(1)
                    elapsed += 1
        finally:
            self.release_lock()
            logger.info("FX Scheduler stopped. Lock released.")


def main():
    parser = argparse.ArgumentParser(description="Finora FX Rate Fetching Scheduler")
    parser.add_argument("--once", action="store_true", help="Execute a single fetch run and exit")
    parser.add_argument("--interval", type=int, default=None, help="Poll interval in minutes (default from config: 60)")
    parser.add_argument("--dry-run", action="store_true", help="Run without persisting new observations")
    parser.add_argument("--force-enable", action="store_true", help="Run even if FX_SCHEDULER_ENABLED is false in settings")

    args = parser.parse_args()

    if not args.once and not settings.FX_SCHEDULER_ENABLED and not args.force_enable:
        logger.info("FX Scheduler is disabled by default (FX_SCHEDULER_ENABLED=false). Use --force-enable or set FX_SCHEDULER_ENABLED=true in .env to run daemon.")
        sys.exit(0)

    scheduler = FxScheduler(interval_minutes=args.interval, dry_run=args.dry_run)

    if args.once:
        success = scheduler.run_once()
        sys.exit(0 if success else 1)
    else:
        scheduler.run_loop()


if __name__ == "__main__":
    main()
