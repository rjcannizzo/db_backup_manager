import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(backup_root: str) -> logging.Logger:
    """Return a rotating file logger for db_backup_manager.

    Log file location: <backup_root>/logs/db_backup_manager.log
    Logs errors only — routine operations are reported via Rich in the CLI.
    Rotating: 1MB max per file, 3 backups kept.
    """
    log_dir = Path(backup_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("db_backup_manager")

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.ERROR)

    handler = RotatingFileHandler(
        log_dir / "db_backup_manager.log",
        maxBytes=1_000_000,  # 1MB
        backupCount=3,
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)s  %(message)s")
    )
    logger.addHandler(handler)

    return logger