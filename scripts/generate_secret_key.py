"""Print a cryptographically random value suitable for RPA_SAP_SECRET_KEY.

Usage:
    python scripts/generate_secret_key.py

Copy the output into backend/.env (local) or your deployment's secret store
(Docker/compose env, cloud secrets manager, etc.) as RPA_SAP_SECRET_KEY.
Never commit the generated value to source control.
"""

import secrets

if __name__ == "__main__":
    print(secrets.token_urlsafe(64))
