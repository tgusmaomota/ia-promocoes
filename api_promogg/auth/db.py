import os
import sqlite3
from pathlib import Path


DEFAULT_AUTH_DB_PATH = Path("auth_dev.db")
AUTH_DB_ENV = "PROMOGG_AUTH_DB_PATH"


def auth_db_path() -> Path:
    return Path(os.environ.get(AUTH_DB_ENV, DEFAULT_AUTH_DB_PATH))


def conectar_auth_db(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path is not None else auth_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
