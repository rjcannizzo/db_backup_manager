import sqlite3
from pathlib import Path

from db_backup_manager.logger import get_logger


def vacuum_database(appname: str, db_path: str, backup_root: str) -> None:
    """Run VACUUM on the source SQLite database.

    Reclaims freed pages and defragments the database file.
    Requires a brief exclusive lock — safe for low-traffic personal apps.
    Only runs if vacuum_schedule is set in the app's config.
    """
    logger = get_logger(backup_root)

    try:
        # conn = sqlite3.connect(db_path)
        conn = sqlite3.connect(str(Path(db_path).expanduser()))
        conn.execute("VACUUM")
        conn.close()
    except Exception as e:
        logger.error(f"[{appname}] Vacuum failed: {e}")
        raise