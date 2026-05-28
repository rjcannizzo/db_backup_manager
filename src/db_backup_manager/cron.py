def get_cron_entries(appname: str, config: dict) -> dict:
    """Generate crontab entry strings for a registered app.

    Returns a dict with 'backup' and 'vacuum' crontab lines
    derived from the app's config.
    """
    return {
        "backup": f"{config['backup_frequency']} db-backup-manager backup {appname}",
        "vacuum": f"{config['vacuum_schedule']} db-backup-manager vacuum {appname}",
    }


def format_cron_entries(appname: str, entries: dict) -> str:
    """Format crontab entries as a readable string for display."""
    return (
        f"\n# {appname}\n"
        f"{entries['backup']}\n"
        f"{entries['vacuum']}\n"
    )