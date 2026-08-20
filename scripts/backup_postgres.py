"""Back up the `postgres` compose service's database to a local file.

The backend's Postgres database is the only container with state that
actually matters to preserve (users, workflow runs, exceptions, audit log —
real application state). The mock-sap/mock-non-sap services use SQLite and
reseed synthetic data on every startup, so they're intentionally not backed
up here.

Usage:
    python scripts/backup_postgres.py [--keep N]

Requires the `postgres` service to be running (`docker compose up -d
postgres` or the full stack) and the `docker` CLI on PATH. Writes a
timestamped pg_dump custom-format archive to ./backups/, then deletes older
backups beyond --keep (default 14).

Restore with scripts/restore_postgres.py.
"""

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = REPO_ROOT / "backups"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", type=int, default=14, help="Number of recent backups to retain")
    parser.add_argument(
        "--db", default=os.environ.get("POSTGRES_DB", "rpa_sap"), help="Database name"
    )
    parser.add_argument(
        "--user", default=os.environ.get("POSTGRES_USER", "rpa_sap"), help="Database user"
    )
    args = parser.parse_args()

    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = BACKUP_DIR / f"rpa_sap_{timestamp}.dump"

    cmd = [
        "docker", "compose", "exec", "-T", "postgres",
        "pg_dump", "-U", args.user, "-Fc", args.db,
    ]
    print(f"Running: {' '.join(cmd)}")
    with open(out_path, "wb") as f:
        result = subprocess.run(cmd, cwd=REPO_ROOT, stdout=f)

    if result.returncode != 0 or out_path.stat().st_size == 0:
        out_path.unlink(missing_ok=True)
        print("Backup failed — is the postgres service running? (docker compose ps)", file=sys.stderr)
        sys.exit(1)

    print(f"Backup written: {out_path} ({out_path.stat().st_size:,} bytes)")

    backups = sorted(BACKUP_DIR.glob("rpa_sap_*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in backups[args.keep:]:
        print(f"Removing old backup beyond --keep {args.keep}: {stale.name}")
        stale.unlink()


if __name__ == "__main__":
    main()
