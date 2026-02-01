import os
import time
import logging
from datetime import datetime

from croniter import croniter

from task_runtime import ensure_data_dirs, TASKS_ROOT, clear_stale_lock, read_text, run_task_background

# Setup logging
log_file = "/var/log/artillery_scheduler.log"
try:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [scheduler] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_local_time() -> datetime:
    """
    Get current local time as a NAIVE datetime in the container's local timezone.
    Respects the TZ environment variable set in the container.
    This is compatible with croniter.match() which expects naive local time.
    """
    # Use time.localtime() to get local time tuple respecting TZ env var
    local_timestamp = time.time()
    local_struct = time.localtime(local_timestamp)
    
    # Create a naive datetime from the local time struct
    # This is what croniter.match() expects
    naive_local = datetime(
        year=local_struct.tm_year,
        month=local_struct.tm_mon,
        day=local_struct.tm_mday,
        hour=local_struct.tm_hour,
        minute=local_struct.tm_min,
        second=local_struct.tm_sec,
    )
    return naive_local


def normalize_to_minute(now: datetime) -> datetime:
    return now.replace(second=0, microsecond=0)


def main():
    try:
        ensure_data_dirs()
    except Exception as exc:
        logger.error(f"Failed to ensure data directories: {exc}")
        return

    # Verify TASKS_ROOT is accessible
    if not TASKS_ROOT:
        logger.error("TASKS_ROOT is not set")
        return
    
    if not os.path.isdir(TASKS_ROOT):
        logger.error(f"TASKS_ROOT does not exist: {TASKS_ROOT}")
        return

    now = get_local_time()
    now_minute = normalize_to_minute(now)

    try:
        entries = list(os.scandir(TASKS_ROOT))
    except Exception as exc:
        logger.error(f"Error scanning tasks directory: {exc}")
        return

    if not entries:
        return

    found_any_cron = False

    for entry in sorted(entries, key=lambda e: e.name):
        if not entry.is_dir():
            continue

        slug = entry.name
        task_folder = entry.path

        cron_path = os.path.join(task_folder, "cron.txt")
        cron_expr = read_text(cron_path)
        
        if not cron_expr:
            continue

        found_any_cron = True

        paused_path = os.path.join(task_folder, "paused")
        if os.path.exists(paused_path):
            continue

        lock_path = os.path.join(task_folder, "lock")
        
        # Check if cron expression matches current time (at minute precision)
        try:
            matches = croniter.match(cron_expr, now_minute)
        except Exception as exc:
            logger.error(f"Task '{slug}': Invalid cron expression '{cron_expr}' - {exc}")
            matches = False
        
        if not matches:
            continue

        # Check if lock is clear
        if not clear_stale_lock(slug, task_folder):
            continue

        # Create lock atomically to avoid races
        try:
            with open(lock_path, "x"):
                pass
        except FileExistsError:
            continue
        except Exception as exc:
            logger.error(f"Task '{slug}': Failed to create lock - {exc}")
            continue
        
        try:
            logger.info(f"Running task '{slug}' (cron: '{cron_expr}')")
            run_task_background(task_folder)
        except Exception as exc:
            logger.error(f"Task '{slug}': Error running task - {exc}")
            # Clean up the lock file if task startup failed
            try:
                os.remove(lock_path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
