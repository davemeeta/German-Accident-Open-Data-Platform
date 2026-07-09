"""Database helpers: open a connection (FK enforced) and initialise the schema."""
from pathlib import Path
import sqlite3

from etl.config import DB_PATH, SCHEMA_PATH


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection, schema_path: Path = SCHEMA_PATH) -> None:
    conn.executescript(Path(schema_path).read_text(encoding="utf-8"))
    conn.commit()


def reset_database(db_path: Path = DB_PATH) -> None:
    """Delete the DB file so the next init starts clean (reproducible imports)."""
    p = Path(db_path)
    if p.exists():
        p.unlink()