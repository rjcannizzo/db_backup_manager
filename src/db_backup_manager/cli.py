import typer
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

from db_backup_manager.config import (
    load_config,
    validate_settings,
    get_backup_dir,
    write_app_config,
)
from db_backup_manager.cron import get_cron_entries, format_cron_entries

app = typer.Typer(help="SQLite database backup manager.")
console = Console()

# Cron expression presets
BACKUP_FREQUENCY_PRESETS = {
    "1": ("Once daily at midnight",       "0 0 * * *"),
    "2": ("Twice daily (midnight, noon)",  "0 0,12 * * *"),
    "4": ("Every 6 hours",                "0 */6 * * *"),
    "6": ("Every 4 hours",                "0 */4 * * *"),
    "8": ("Every 3 hours",                "0 */3 * * *"),
    "24": ("Every hour",                  "0 * * * *"),
}

VACUUM_SCHEDULE_PRESETS = {
    "1": ("Monthly (1st of month, midnight)", "0 0 1 * *"),
    "2": ("Weekly (Sunday midnight)",         "0 0 * * 0"),
    "3": ("Never",                            None),
}


def prompt_backup_frequency() -> str:
    """Prompt user to select a backup frequency preset."""
    console.print("\n[bold]Backup frequency:[/bold]")
    for key, (label, expr) in BACKUP_FREQUENCY_PRESETS.items():
        console.print(f"  {key}) {label}  [dim]({expr})[/dim]")
    choice = typer.prompt("Select an option").strip()
    while choice not in BACKUP_FREQUENCY_PRESETS:
        console.print("[red]Invalid choice. Please select a valid option.[/red]")
        choice = typer.prompt("Select an option").strip()
    return BACKUP_FREQUENCY_PRESETS[choice][1]


def prompt_vacuum_schedule() -> str | None:
    """Prompt user to select a vacuum schedule preset."""
    console.print("\n[bold]Vacuum schedule:[/bold]")
    for key, (label, _) in VACUUM_SCHEDULE_PRESETS.items():
        console.print(f"  {key}) {label}")
    choice = typer.prompt("Select an option").strip()
    while choice not in VACUUM_SCHEDULE_PRESETS:
        console.print("[red]Invalid choice. Please select a valid option.[/red]")
        choice = typer.prompt("Select an option").strip()
    return VACUUM_SCHEDULE_PRESETS[choice][1]


@app.command()
def register(appname: str = typer.Argument(..., help="Name of the app to register")):
    """Register a new app for backup management."""

    config = load_config()
    validate_settings(config)

    # Check if app is already registered
    if appname in config:
        console.print(f"\n[red]✗ '{appname}' is already registered.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Registering app:[/bold] {appname}")

    # Prompt for app details
    db_path = typer.prompt("\nPath to the SQLite database").strip()
    if not Path(db_path).exists():
        console.print(f"[yellow]⚠ Warning: {db_path} does not exist. Registering anyway.[/yellow]")

    backup_frequency = prompt_backup_frequency()
    vacuum_schedule = prompt_vacuum_schedule()

    backups_per_day = typer.prompt(
        "\nHow many backups per day", default=4
    )
    retention_days = typer.prompt(
        "How many days to retain backups", default=30
    )
    max_backups = int(backups_per_day) * int(retention_days)
    console.print(f"[dim]  → max_backups set to {max_backups} "
                  f"({backups_per_day}/day × {retention_days} days)[/dim]")

    # Build data dict — omit vacuum_schedule if user selected Never
    data = {
        "db_path": db_path,
        "backup_frequency": backup_frequency,
        "max_backups": max_backups,
    }
    if vacuum_schedule:
        data["vacuum_schedule"] = vacuum_schedule

    # Create backup directory
    backup_dir = get_backup_dir(appname, config)
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Save to config
    write_app_config(appname, data)

    console.print(f"\n[green]✓ '{appname}' registered successfully.[/green]")
    console.print(f"  Backup directory: {backup_dir}")

    # Print crontab entries
    if vacuum_schedule:
        entries = get_cron_entries(appname, data)
        formatted = format_cron_entries(appname, entries)
        console.print(
            Panel(
                f"[bold]Add these entries to your crontab:[/bold]\n"
                f"[dim](run: crontab -e)[/dim]\n"
                f"{formatted}",
                title="Crontab",
                border_style="blue",
            )
        )
    else:
        entries = {"backup": get_cron_entries(appname, data)["backup"]}
        console.print(
            Panel(
                f"[bold]Add this entry to your crontab:[/bold]\n"
                f"[dim](run: crontab -e)[/dim]\n\n"
                f"# {appname}\n{entries['backup']}\n",
                title="Crontab",
                border_style="blue",
            )
        )