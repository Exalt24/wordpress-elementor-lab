"""Prints fresh random passwords for the lab as an env file: python scripts/make_env.py > build/.env (build/ is ignored by git)."""
import secrets

for name in ("LAB_DB_PW", "LAB_DB_ROOT_PW", "LAB_ADMIN_PW"):
    print(f"{name}={secrets.token_urlsafe(14)}")
