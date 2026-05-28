import tomllib
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".db_backup_manager" / "config.toml"


def get_config_path() -> Path:
    """Return the path to the config file."""
    return CONFIG_PATH


def load_config() -> dict:
    """Read and return the config file contents.
    Exits with a clear error message if the config file is not found.
    """
    config_path = get_config_path()
    if not config_path.exists():
        print(
            f"\n✗ Config file not found at {config_path}\n\n"
            "Please complete the one-time setup:\n"
            "  1. Create the directory:  mkdir ~/.db_backup_manager\n"
            "  2. Create the config file: touch ~/.db_backup_manager/config.toml\n"
            "  3. Add the [settings] block to config.toml:\n\n"
            "       [settings]\n"
            "       backup_root = \"/path/to/your/backups\"\n"
        )
        sys.exit(1)

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def validate_settings(config: dict) -> None:
    """Check that [settings] and backup_root exist in the config.
    Exits with a clear error message if missing.
    """
    if "settings" not in config or "backup_root" not in config.get("settings", {}):
        print(
            "\n✗ backup_root not found in config.\n\n"
            "Please add the following to ~/.db_backup_manager/config.toml:\n\n"
            "  [settings]\n"
            "  backup_root = \"/path/to/your/backups\"\n"
        )
        sys.exit(1)


def get_backup_dir(appname: str, config: dict) -> Path:
    """Derive the per-app backup directory from backup_root / appname."""
    return Path(config["settings"]["backup_root"]) / appname


def write_app_config(appname: str, data: dict) -> None:
    """Append a new app entry to the config file."""
    config_path = get_config_path()
    entry = (
        f"\n[{appname}]\n"
        f"db_path = \"{data['db_path']}\"\n"
        f"backup_frequency = \"{data['backup_frequency']}\"\n"
        f"max_backups = {data['max_backups']}\n"
    )
    if "vacuum_schedule" in data:
        entry += f"vacuum_schedule = \"{data['vacuum_schedule']}\"\n"
    with open(config_path, "a") as f:
        f.write(entry)