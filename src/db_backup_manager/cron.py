import shutil


def get_cmd() -> str:
    """Return the full path to db-backup-manager or fall back to the command name."""
    return shutil.which("db-backup-manager") or "db-backup-manager"


def get_cron_entries(appname: str, config: dict, backup_root: str) -> dict:
    """Generate crontab entry strings for a registered app.

    Returns a dict with 'backup' and 'vacuum' crontab lines
    derived from the app's config. Includes full command path
    and log redirection.
    """
    cmd = get_cmd()
    log_path = f"{backup_root}/logs/cron.log"

    entries = {
        "backup": (
            f"{config['backup_frequency']} "
            f"{cmd} backup {appname} "
            f">> {log_path} 2>&1"
        ),
    }
    if "vacuum_schedule" in config:
        entries["vacuum"] = (
            f"{config['vacuum_schedule']} "
            f"{cmd} vacuum {appname} "
            f">> {log_path} 2>&1"
        )
    return entries