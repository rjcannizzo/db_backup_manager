# db_backup_manager — Game Plan

## Overview

A CLI-first Python tool for managing SQLite database backups on an Ubuntu server.
Packaged as an installable Python package using `uv`. Designed with clean separation
between frontend (CLI, future TUI/web) and core logic.

---

## Goals & Scope

- Back up a collection of small SQLite databases on a personal Ubuntu server
- Per-app configuration: backup frequency, retention limit, vacuum schedule
- Backup scheduling via **cron** (user-managed, assisted by `cron-show`)
- Backup pruning handled by Python after each backup run
- CLI frontend using **Typer** + **Rich** for output
- Optional future frontends: **Textual** (TUI), Flask/NiceGUI (web)

---

## Project Directory Structure

```
db_backup_manager/              # project root
├── pyproject.toml
├── README.md
└── src/
    └── db_backup_manager/      # package source
        ├── __init__.py
        ├── cli.py              # Typer entry points (thin layer — no business logic)
        ├── config.py           # TOML read/write (~/.db_backup_manager/config.toml)
        ├── backup.py           # sqlite3 backup logic
        ├── pruner.py           # retention enforcement (keep newest N backups)
        ├── vacuum.py           # sqlite3 VACUUM logic
        ├── logger.py           # centralized error logging
        ├── cron.py             # cron entry generation for cron-show command
        └── tui.py              # Textual TUI (future)
```

### Backup Directory Layout

```
~/db_backups/
├── logs/
│   └── db_backup_manager.log    # single rotating log for all apps
├── myapp/
│   ├── backup_20260101_060000.db
│   ├── backup_20260101_120000.db
│   └── ...
└── otherapp/
    ├── backup_20260101_060000.db
    └── ...
```

### Packaging

`pyproject.toml` entry point:
```toml
[project.scripts]
db-backup-manager = "db_backup_manager.cli:app"
```

### Bootstrap with uv

```bash
uv init db_backup_manager --package
cd db_backup_manager
uv add typer
uv pip install -e .
```

---

## Build Order

1. **`config.py`** — everything else depends on reading/writing the config
2. **`register` command** — gets an app into the config so we have real data to work with
3. **`backup.py`** — core backup logic using `sqlite3` backup API
4. **`pruner.py`** — retention enforcement, runs after each backup
5. **`vacuum.py`** — sqlite3 VACUUM on the source database
6. **`logger.py`** — centralized error logging with rotation
7. **`cron.py`** — cron entry generation for `cron-show` command
8. **`list` command** — Rich table, needs config + backup dirs populated first

---

## Configuration

Location: `~/.db_backup_manager/config.toml`

Read with `tomllib` (stdlib, Python 3.11+). Written manually as a formatted string
— no `tomli-w` dependency needed given the simple, flat config structure.

### Example

```toml
[myapp]
db_path = "/home/user/apps/myapp/data.db"
backup_dir = "/home/user/db_backups/myapp"
backup_frequency = "0 */6 * * *"   # cron expression — every 6 hours
max_backups = 120                   # 4/day x 30 days
vacuum_schedule = "0 0 1 * *"      # cron expression — midnight, 1st of month

[otherapp]
db_path = "/home/user/apps/otherapp/data.db"
backup_dir = "/home/user/db_backups/otherapp"
backup_frequency = "0 */4 * * *"
max_backups = 90
vacuum_schedule = "0 0 1 * *"
```

---

## CLI Commands

```bash
db-backup-manager register <appname>     # register a new app (prompts for config values)
db-backup-manager list                   # list all registered apps with status
db-backup-manager backup <appname>       # run a backup + prune old backups
db-backup-manager vacuum <appname>       # run VACUUM on the source database
db-backup-manager cron-show <appname>    # print crontab entries for one app
db-backup-manager cron-show --all        # print crontab entries for all apps
```

---

## Core Module Notes

### `config.py`
Reads `~/.db_backup_manager/config.toml` using `tomllib` (stdlib, Python 3.11+).
Writes new app entries as formatted strings appended to the config file:

```python
def write_app_config(appname: str, config: dict, config_path: Path) -> None:
    entry = f"""
[{appname}]
db_path = "{config['db_path']}"
backup_dir = "{config['backup_dir']}"
backup_frequency = "{config['backup_frequency']}"
max_backups = {config['max_backups']}
vacuum_schedule = "{config['vacuum_schedule']}"
"""
    with open(config_path, "a") as f:
        f.write(entry)
```

### `backup.py`
Uses Python's built-in `sqlite3` backup API — safe for live databases:

```python
import sqlite3
from datetime import datetime
from pathlib import Path

def backup_database(db_path: str, backup_dir: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(backup_dir) / f"backup_{timestamp}.db"
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(backup_path)
    src.backup(dst)
    dst.close()
    src.close()
    return backup_path
```

### `pruner.py`
Keeps the N most recent backups, deletes the rest:

```python
from pathlib import Path

def prune_backups(backup_dir: str, max_backups: int) -> list[Path]:
    backups = sorted(Path(backup_dir).glob("backup_*.db"))
    to_delete = backups[:-max_backups] if len(backups) > max_backups else []
    for f in to_delete:
        f.unlink()
    return to_delete
```

### `vacuum.py`
Uses standard `sqlite3` — no external dependencies:

```python
import sqlite3

def vacuum_database(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("VACUUM")
    conn.close()
```

### `logger.py`
Single rotating log file for all apps under the shared `db_backups/logs/` directory.
Logs errors only — routine operations are handled by Rich status output:

```python
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def get_logger(backup_root: str) -> logging.Logger:
    log_dir = Path(backup_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("db_backup_manager")
    logger.setLevel(logging.ERROR)

    handler = RotatingFileHandler(
        log_dir / "db_backup_manager.log",
        maxBytes=1_000_000,   # 1MB
        backupCount=3
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s  %(levelname)s  %(message)s")
    )
    logger.addHandler(handler)
    return logger
```

### `cron.py`
Generates crontab lines from config — never touches the actual crontab:

```python
def get_cron_entries(appname: str, config: dict) -> dict:
    return {
        "backup": f"{config['backup_frequency']}  db-backup-manager backup {appname}",
        "vacuum": f"{config['vacuum_schedule']}  db-backup-manager vacuum {appname}",
    }
```

---

## Scheduling Strategy

- **No in-process scheduler** (no APScheduler) — keeps the app simple and stateless
- Cron drives all scheduling; `db-backup-manager` is invoked by cron per entry
- `cron-show` assists the user in setting up crontab entries without automating it

### Example crontab (user-managed)

```cron
# myapp backups — every 6 hours
0 */6 * * *  db-backup-manager backup myapp

# myapp vacuum — midnight, 1st of each month
0 0 1 * *    db-backup-manager vacuum myapp
```

---

## Vacuum Notes

- `VACUUM` is run directly on the **source database** to reclaim freed pages and defragment
- Vacuum and backup are **decoupled** — vacuum runs on its own schedule; the next
  regular backup will naturally capture the vacuumed state
- `auto_vacuum = FULL` is an alternative worth exposing as a per-app config option
  for users who prefer automatic compaction over scheduled maintenance

---

## Output & Reporting (Rich)

- `db-backup-manager list` → Rich table: app name, db path, last backup, backup count, next scheduled run
- `db-backup-manager cron-show` → styled table of crontab entries
- Backup/vacuum commands → colored status lines (`✓` / `✗`)

---

## Frontend Layers (Separation of Concerns)

All business logic lives in core modules. Frontends are thin:

| Layer | File | Status |
|---|---|---|
| CLI | `cli.py` (Typer + Rich) | Phase 1 |
| TUI | `tui.py` (Textual) | Phase 2 |
| Web | `web.py` (Flask or NiceGUI) | Phase 3 |

---

## Dependencies

| Package | Purpose | Notes |
|---|---|---|
| `typer` | CLI framework | Includes Rich |
| `rich` | Output formatting | Bundled with Typer |
| `textual` | TUI (future) | Optional, phase 2 |

`sqlite3`, `pathlib`, `datetime`, `logging`, `tomllib` — all stdlib, no extra cost.

---

## Open Questions / Future Considerations

- Backup file format: plain `.db` or compressed `.db.gz`? (size likely not a concern for small DBs)
- `register` command: interactive prompts vs CLI flags (e.g. `--db-path`, `--frequency`)?
- Should `backup --all` and `vacuum --all` be supported for batch operations?
