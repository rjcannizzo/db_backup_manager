import typer
from rich.console import Console
from rich.rule import Rule
from pathlib import Path
from typing import Optional

from db_backup_manager.config import (
    load_config,
    validate_settings,
    get_backup_dir,
    write_app_config,
)
from db_backup_manager.cron import get_cron_entries

app = typer.Typer(help="SQLite database backup manager.")
console = Console()

# Cron expression presets
BACKUP_FREQUENCY_PRESETS = {
    "1": ("Once daily at midnight",      "0 0 * * *"),
    "2": ("Twice daily (midnight, noon)", "0 0,12 * * *"),
    "4": ("Every 6 hours",               "0 */6 * * *"),
    "6": ("Every 4 hours",               "0 */4 * * *"),
    "8": ("Every 3 hours",               "0 */3 * * *"),
    "24": ("Every hour",                 "0 * * * *"),
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


def print_cron_entries(appname: str, data: dict, backup_root: str) -> None:
    """Print crontab entries as plain styled text for easy copying."""
    entries = get_cron_entries(appname, data, backup_root)
    console.print("\n[bold]Add these entries to your crontab[/bold] [dim](crontab -e):[/dim]")
    console.print(Rule(style="blue"))
    console.print(f"[cyan]# {appname}[/cyan]")
    console.print(entries["backup"])
    if "vacuum" in entries:
        console.print(entries["vacuum"])
    console.print(Rule(style="blue"))


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

    backups_per_day = typer.prompt("\nHow many backups per day", default=4)
    retention_days = typer.prompt("How many days to retain backups", default=30)
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

    print_cron_entries(appname, data, config["settings"]["backup_root"])


@app.command()
def show(appname: Optional[str] = typer.Argument(None, help="App name (omit for all apps)")):
    """Show crontab entries for one app or all apps."""

    config = load_config()
    validate_settings(config)

    # Get list of registered apps (exclude [settings])
    apps = {k: v for k, v in config.items() if k != "settings"}

    if not apps:
        console.print("\n[yellow]No apps registered yet. Run: db-backup-manager register <appname>[/yellow]")
        raise typer.Exit()

    if appname:
        if appname not in config:
            console.print(f"\n[red]✗ '{appname}' is not registered.[/red]")
            raise typer.Exit(1)
        apps = {appname: config[appname]}

    console.print("\n[bold]Crontab entries[/bold] [dim](crontab -e):[/dim]")
    console.print(Rule(style="blue"))
    for name, data in apps.items():
        entries = get_cron_entries(name, data, backup_root)
        console.print(f"[cyan]# {name}[/cyan]")
        console.print(entries["backup"])
        if "vacuum" in entries:
            console.print(entries["vacuum"])
        console.print()
    console.print(Rule(style="blue"))


@app.command()
def backup(appname: str = typer.Argument(..., help="Name of the registered app to back up")):
    """Run a backup for a registered app and prune old backups."""
    from db_backup_manager.backup import backup_database
    from db_backup_manager.pruner import prune_backups

    config = load_config()
    validate_settings(config)

    if appname not in config:
        console.print(f"\n[red]✗ '{appname}' is not registered.[/red]")
        raise typer.Exit(1)

    app_config = config[appname]
    backup_root = config["settings"]["backup_root"]
    backup_dir = get_backup_dir(appname, config)

    try:
        backup_path = backup_database(appname, app_config["db_path"], str(backup_dir), backup_root)
        console.print(f"\n[green]✓ Backup complete:[/green] {backup_path.name}")
    except Exception as e:
        console.print(f"\n[red]✗ Backup failed: {e}[/red]")
        raise typer.Exit(1)

    try:
        deleted = prune_backups(appname, str(backup_dir), app_config["max_backups"], backup_root)
        if deleted:
            console.print(f"  Pruned {len(deleted)} old backup(s).")
    except Exception as e:
        console.print(f"[red]✗ Pruning failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def vacuum(appname: str = typer.Argument(..., help="Name of the registered app to vacuum")):
    """Run VACUUM on the source database for a registered app."""
    from db_backup_manager.vacuum import vacuum_database

    config = load_config()
    validate_settings(config)

    if appname not in config:
        console.print(f"\n[red]✗ '{appname}' is not registered.[/red]")
        raise typer.Exit(1)

    app_config = config[appname]
    backup_root = config["settings"]["backup_root"]

    if "vacuum_schedule" not in app_config:
        console.print(f"\n[yellow]⚠ '{appname}' has no vacuum schedule configured.[/yellow]")

    try:
        vacuum_database(appname, app_config["db_path"], backup_root)
        console.print(f"\n[green]✓ Vacuum complete:[/green] {app_config['db_path']}")
    except Exception as e:
        console.print(f"\n[red]✗ Vacuum failed: {e}[/red]")
        raise typer.Exit(1)


@app.command(name="list")
def list_apps():
    """List all registered apps with backup status."""
    from rich.table import Table

    config = load_config()
    validate_settings(config)

    apps = {k: v for k, v in config.items() if k != "settings"}

    if not apps:
        console.print("\n[yellow]No apps registered yet. Run: db-backup-manager register <appname>[/yellow]")
        raise typer.Exit()

    backup_root = config["settings"]["backup_root"]

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("App", style="cyan")
    table.add_column("Database path")
    table.add_column("Backups", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Latest backup", justify="left")
    table.add_column("Vacuum", justify="left")

    for appname, app_config in apps.items():
        backup_dir = Path(backup_root) / appname
        backups = sorted(backup_dir.glob("backup_*.db")) if backup_dir.exists() else []
        backup_count = str(len(backups))
        max_backups = str(app_config["max_backups"])

        if backups:
            # Parse timestamp from filename: backup_YYYYMMDD_HHMMSS.db
            latest = backups[-1].stem.replace("backup_", "")
            latest_str = f"{latest[:4]}-{latest[4:6]}-{latest[6:8]} {latest[9:11]}:{latest[11:13]}:{latest[13:15]}"
        else:
            latest_str = "[dim]none[/dim]"

        vacuum = app_config.get("vacuum_schedule", "[dim]none[/dim]")

        table.add_row(appname, app_config["db_path"], backup_count, max_backups, latest_str, vacuum)

    console.print()
    console.print(table)
    console.print()