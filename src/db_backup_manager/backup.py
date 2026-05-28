import sqlite3
from datetime import datetime
from pathlib import Path

from db_backup_manager.logger import get_logger


def backup_database(appname: str, db_path: str, backup_dir: str, backup_root: str) -> Path:
    """Back up a SQLite database to the backup directory.

    Uses sqlite3's built-in backup API which is safe for live databases.
    Backup filename format: backup_YYYYMMDD_HHMMSS.db

    Returns the path to the created backup file.
    Raises an exception on failure after logging the error.
    """
    logger = get_logger(backup_root)

    backup_dir_path = Path(backup_dir)
    backup_dir_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir_path / f"backup_{timestamp}.db"

    try:
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
    except Exception as e:
        logger.error(f"[{appname}] Backup failed: {e}")
        raise

    return backup_path