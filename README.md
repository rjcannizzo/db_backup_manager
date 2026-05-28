# db-backup-manager

A CLI tool for managing SQLite database backups on Ubuntu. Backs up multiple databases
on a configurable schedule, enforces retention limits, and optionally runs `VACUUM` to
keep source databases compact.

---

## Requirements

- Ubuntu (or any Linux system with cron)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager

---

## Installation

### From GitHub

```bash
git clone https://github.com/yourusername/db_backup_manager.git
cd db_backup_manager
uv tool install .
```

Verify the install:
```bash
db-backup-manager --help
```

### For development (editable install)

```bash
git clone https://github.com/yourusername/db_backup_manager.git
cd db_backup_manager
uv pip install -e .
uv run db-backup-manager --help
```

---

## One-Time Setup

Before registering any apps, complete these two steps:

**1. Create the config directory and file:**
```bash
mkdir ~/.db_backup_manager
touch ~/.db_backup_manager/config.toml
```

**2. Add the `[settings]` block to `config.toml`:**
```toml
[settings]
backup_root = "/home/youruser/db_backups"
```

`backup_root` is the root directory where all backups and logs will be stored.
Each registered app gets its own subdirectory: `backup_root/<appname>/`.

---

## Backup Directory Layout

```
~/db_backups/
├── logs/
│   └── db_backup_manager.log    # rotating error log for all apps
├── myapp/
│   ├── backup_20260101_000000.db
│   ├── backup_20260101_060000.db
│   └── ...
└── otherapp/
    ├── backup_20260101_000000.db
    └── ...
```

---

## Usage

### Register an app

```bash
db-backup-manager register <appname>
```

Prompts for:
- Path to the SQLite database
- Backup frequency (preset options)
- Vacuum schedule (preset options or never)
- Backups per day and retention days (used to calculate `max_backups`)

At the end of registration, crontab entries are printed for easy copy/paste.

Example session:
```
Registering app: myapp

Path to the SQLite database: /home/user/apps/myapp/data.db

Backup frequency:
  1) Once daily at midnight       (0 0 * * *)
  2) Twice daily (midnight, noon) (0 0,12 * * *)
  4) Every 6 hours                (0 */6 * * *)
  6) Every 4 hours                (0 */4 * * *)
  8) Every 3 hours                (0 */3 * * *)
  24) Every hour                  (0 * * * *)
Select an option: 4

Vacuum schedule:
  1) Monthly (1st of month, midnight)
  2) Weekly (Sunday midnight)
  3) Never
Select an option: 1

How many backups per day [4]:
How many days to retain backups [30]:
  → max_backups set to 120 (4/day × 30 days)

✓ myapp registered successfully.
  Backup directory: /home/user/db_backups/myapp

Add these entries to your crontab (crontab -e):
──────────────────────────────────────────────────────
# myapp
0 */6 * * * db-backup-manager backup myapp
0 0 1 * * db-backup-manager vacuum myapp
──────────────────────────────────────────────────────
```

### Set up cron

Run `crontab -e` and paste the lines printed by `register`. Only paste the raw cron
lines — do not include the separator lines or comments from the output panel.

To review entries at any time:
```bash
db-backup-manager show           # all apps
db-backup-manager show <appname> # one app
```

### Run a backup manually

```bash
db-backup-manager backup <appname>
```

Backs up the database and prunes old backups exceeding `max_backups`.

### Run vacuum manually

```bash
db-backup-manager vacuum <appname>
```

Runs `VACUUM` on the source database to reclaim freed space and defragment.
Note: vacuum and backup are independent — vacuum does not trigger a backup.

### List all apps

```bash
db-backup-manager list
```

Displays a table showing each registered app, database path, backup count,
max backups, latest backup timestamp, and vacuum schedule.

---

## Config File Reference

Location: `~/.db_backup_manager/config.toml`

```toml
[settings]
backup_root = "/home/user/db_backups"    # required — root backup directory

[myapp]
db_path = "/home/user/apps/myapp/data.db"
backup_frequency = "0 */6 * * *"         # cron expression
max_backups = 120                         # total backups to retain
vacuum_schedule = "0 0 1 * *"            # optional — omit to disable vacuum
```

Per-app backup directory is derived automatically as `backup_root/<appname>`.

---

## Logging

Errors are logged to `<backup_root>/logs/db_backup_manager.log`.
The log file rotates at 1MB with 3 backups kept. Routine operations
(successful backups, pruning) are not logged — check `db-backup-manager list`
for current status.

---

## Commands Reference

| Command | Description |
|---|---|
| `register <appname>` | Register a new app interactively |
| `list` | Show all registered apps and backup status |
| `backup <appname>` | Run a backup and prune old backups |
| `vacuum <appname>` | Run VACUUM on the source database |
| `show` | Show crontab entries for all apps |
| `show <appname>` | Show crontab entries for one app |

---

## Future Plans

- TUI interface using Textual
- Web interface using Flask or NiceGUI
- `backup --all` and `vacuum --all` for batch operations