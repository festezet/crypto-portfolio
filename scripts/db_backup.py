#!/usr/bin/env python3
"""Backup automatique des bases de donnees - crypto-portfolio"""

from pathlib import Path
from shared_lib.db import backup_database as _shared_backup

DATA_DIR = Path(__file__).parent.parent / "data"
BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 10

DB_FILES = [
    DATA_DIR / "portfolio.db",
]


def backup_database():
    """Backup toutes les DB avec rotation (garde les 10 derniers)."""
    for db_path in DB_FILES:
        result = _shared_backup(str(db_path), str(BACKUP_DIR), max_backups=MAX_BACKUPS)
        if result:
            print(f"[backup] {db_path.name} -> {Path(result).name}")


if __name__ == "__main__":
    backup_database()
