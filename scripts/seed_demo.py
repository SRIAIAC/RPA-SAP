"""Orchestrates a full, deterministic reset + reseed of the whole platform:
main backend DB, mock-sap DB, mock-non-sap DB, and the synthetic document
set. Safe to run against a fresh checkout or to reset an existing one back
to the golden-scenario baseline.

Each service (backend/mock-sap/mock-non-sap) is its own Python package
named `app` with its own venv — importing all three into one process would
collide on `sys.modules["app"]`. Instead, this script shells out to each
service's own venv interpreter with a small inline reset+seed script, which
also matches how these are actually deployed (separate processes/
containers) and reuses each service's already-idempotent seed() functions
verbatim rather than reimplementing them here.

Usage:
    backend\\.venv\\Scripts\\python.exe scripts\\seed_demo.py [--scale small|full]
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_RESET_AND_SEED_TEMPLATE = """
import sys
sys.path.insert(0, r"{service_dir}")

from sqlmodel import SQLModel

from app.database import engine, init_db
from app.models import *  # noqa: F401,F403  (ensure every table is registered before drop_all)

SQLModel.metadata.drop_all(engine)
init_db()

{seed_call}
print("Reseeded {service_name} ({{}} scale)".format("{scale}"))
"""

SERVICES = [
    {
        "name": "backend",
        "dir": ROOT / "backend",
        "venv_python": ROOT / "backend" / ".venv" / "Scripts" / "python.exe",
        "seed_call": (
            "from sqlmodel import Session\n"
            "from app import models_platform  # noqa: F401  (register platform tables too)\n"
            "from app.seed_data import seed\n"
            "from app.seed_data_mailroom import seed_mailroom\n"
            "with Session(engine) as session:\n"
            "    seed(session)\n"
            "    seed_mailroom(session)\n"
        ),
    },
    {
        "name": "mock-sap",
        "dir": ROOT / "mock-systems" / "mock-sap",
        "venv_python": ROOT / "mock-systems" / "mock-sap" / ".venv" / "Scripts" / "python.exe",
        "seed_call": (
            "from sqlmodel import Session\n"
            "from app.seed.generate_synthetic_data import seed_all\n"
            "with Session(engine) as session:\n"
            "    seed_all(session, scale='{scale}')\n"
        ),
    },
    {
        "name": "mock-non-sap",
        "dir": ROOT / "mock-systems" / "mock-non-sap",
        "venv_python": ROOT / "mock-systems" / "mock-non-sap" / ".venv" / "Scripts" / "python.exe",
        "seed_call": (
            "from sqlmodel import Session\n"
            "from app.seed.generate_synthetic_data import seed_all\n"
            "with Session(engine) as session:\n"
            "    seed_all(session, scale='{scale}')\n"
        ),
    },
]


def reseed_service(service: dict, scale: str) -> None:
    python = service["venv_python"]
    if not python.exists():
        print(f"SKIP {service['name']}: venv not found at {python} (run its setup first)")
        return

    seed_call = service["seed_call"].format(scale=scale)
    script = _RESET_AND_SEED_TEMPLATE.format(
        service_dir=service["dir"], seed_call=seed_call, service_name=service["name"], scale=scale
    )
    result = subprocess.run([str(python), "-c", script], cwd=str(service["dir"]), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED reseeding {service['name']}:\n{result.stderr}")
        raise SystemExit(1)
    print(result.stdout.strip() or f"Reseeded {service['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", choices=["small", "full"], default="full")
    parser.add_argument("--skip-documents", action="store_true", help="Skip PDF document generation")
    args = parser.parse_args()

    print(f"=== Resetting and reseeding the platform (scale={args.scale}) ===")
    for service in SERVICES:
        reseed_service(service, args.scale)

    if not args.skip_documents:
        print("=== Generating synthetic documents ===")
        backend_python = ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
        result = subprocess.run(
            [str(backend_python), str(ROOT / "scripts" / "generate_documents.py")],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"Document generation failed:\n{result.stderr}")
            raise SystemExit(1)

    print("=== Done. Restart the three services (or they'll pick this up on next boot). ===")


if __name__ == "__main__":
    sys.exit(main())
