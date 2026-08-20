"""Restore the `postgres` compose service's database from a pg_dump backup.

DESTRUCTIVE: this drops and recreates every object in the target database
before restoring. Only ever run this deliberately, and only ever restore a
backup file you trust (it was produced by scripts/backup_postgres.py on
this same project).

Usage:
    python scripts/restore_postgres.py backups/rpa_sap_20260101_030000.dump --yes

--yes is required to actually perform the restore; without it the script
only prints what it would do.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup_file", type=Path, help="Path to a .dump file from backup_postgres.py")
    parser.add_argument(
        "--db", default=os.environ.get("POSTGRES_DB", "rpa_sap"), help="Database name"
    )
    parser.add_argument(
        "--user", default=os.environ.get("POSTGRES_USER", "rpa_sap"), help="Database user"
    )
    parser.add_argument(
        "--yes", action="store_true", help="Actually perform the restore (required, otherwise dry-run)"
    )
    args = parser.parse_args()

    if not args.backup_file.exists():
        print(f"No such file: {args.backup_file}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "docker", "compose", "exec", "-T", "postgres",
        "pg_restore", "--clean", "--if-exists", "--no-owner",
        "-U", args.user, "-d", args.db,
    ]

    if not args.yes:
        print("DRY RUN (pass --yes to actually restore). Would run:")
        print(f"  {' '.join(cmd)} < {args.backup_file}")
        print(f"This will DROP and recreate all objects in database '{args.db}'.")
        return

    print(f"Restoring {args.backup_file} into database '{args.db}'...")
    with open(args.backup_file, "rb") as f:
        result = subprocess.run(cmd, cwd=REPO_ROOT, stdin=f)

    if result.returncode != 0:
        print("Restore reported errors — check output above.", file=sys.stderr)
        sys.exit(1)

    print("Restore complete.")


if __name__ == "__main__":
    main()
