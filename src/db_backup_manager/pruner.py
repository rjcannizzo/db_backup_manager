from pathlib import Path

from db_backup_manager.logger import get_logger


def prune_backups(appname: str, backup_dir: str, max_backups: int, backup_root: str) -> list[Path]:
    """Remove oldest backups exceeding max_backups.

    Backups are sorted by filename (which encodes the timestamp),
    so oldest files are removed first.

    Returns a list of deleted file paths.
    """
    logger = get_logger(backup_root)

    try:
        backups = sorted(Path(backup_dir).glob("backup_*.db"))
        to_delete = backups[:-max_backups] if len(backups) > max_backups else []
        for f in to_delete:
            f.unlink()
    except Exception as e:
        logger.error(f"[{appname}] Pruning failed: {e}")
        raise

    return to_delete