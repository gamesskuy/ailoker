"""Lapisan database AILoker MVP — backend ganda dengan API identik.

- Lokal / Docker: SQLite via stdlib (DATABASE_PATH / AILOKER_DB / ./ailoker.db).
- Vercel / serverless: Turso (libsql) bila TURSO_URL + TURSO_TOKEN diset.

connect() mengembalikan koneksi dengan .execute() -> kursor yang mendukung
fetchone()/fetchall()/lastrowid, serta .commit()/.close()/.executescript().
Baris hasil mendukung row["kolom"] maupun row[i] (mirip sqlite3.Row),
sehingga app/main.py, app/auth.py, app/seed.py tidak perlu diubah.
"""
import json
import os
import time

_db_env = os.environ.get("DATABASE_PATH") or os.environ.get("AILOKER_DB")
DB_PATH = _db_env or os.path.join(os.path.dirname(os.path.abspath(__file__)), "ailoker.db")

TURSO_URL = os.environ.get("TURSO_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "").strip()
# URL file: (libsql.connect("file:...")) tidak butuh token — berguna untuk tes lokal.
USE_TURSO = bool(TURSO_URL) and (TURSO_URL.startswith("file:") or bool(TURSO_TOKEN))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('seeker','company')),
    name TEXT NOT NULL,
    company_name TEXT,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    skills TEXT DEFAULT '[]',
    experience TEXT DEFAULT '[]',
    education TEXT DEFAULT '[]',
    raw_text TEXT DEFAULT '',
    updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    job_type TEXT NOT NULL DEFAULT 'Penuh Waktu',
    salary_min INTEGER DEFAULT 0,
    salary_max INTEGER DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    points_raw TEXT DEFAULT '',
    fraud_warning TEXT DEFAULT '',
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ai_score INTEGER DEFAULT 0,
    ai_reason TEXT DEFAULT '',
    created_at INTEGER NOT NULL,
    UNIQUE(job_id, user_id)
);
CREATE TABLE IF NOT EXISTS match_cache (
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    gaps TEXT NOT NULL DEFAULT '[]',
    created_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, job_id)
);
"""


class _Row:
    """Baris hasil: dukung row['kolom'] dan row[i] seperti sqlite3.Row."""
    __slots__ = ("_cols", "_vals", "_idx")

    def __init__(self, cols, vals):
        self._cols = cols
        self._vals = tuple(vals)
        self._idx = None

    def _index(self):
        if self._idx is None:
            self._idx = {c: i for i, c in enumerate(self._cols)}
        return self._idx

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._vals[key]
        return self._vals[self._index()[key]]

    def __iter__(self):
        return iter(self._vals)

    def __len__(self):
        return len(self._vals)

    def keys(self):
        return list(self._cols)

    def __repr__(self):  # pragma: no cover
        return f"_Row({dict(zip(self._cols, self._vals))})"


class _Cursor:
    def __init__(self, cur):
        self._cur = cur
        self._cols = [d[0] for d in (cur.description or [])]

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def description(self):
        return self._cur.description

    def _wrap(self, row):
        return None if row is None else _Row(self._cols, row)

    def fetchone(self):
        return self._wrap(self._cur.fetchone())

    def fetchall(self):
        return [self._wrap(r) for r in self._cur.fetchall()]

    def __iter__(self):
        # kursor libsql tidak iterable langsung -> pakai fetchall()
        for r in self._cur.fetchall():
            yield self._wrap(r)


class _Connection:
    """Bungkus koneksi libsql agar API-nya identik dengan sqlite3."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        return _Cursor(self._conn.execute(sql, params))

    def executescript(self, sql):
        return self._conn.executescript(sql)

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def connect():
    if USE_TURSO:
        import libsql  # pip: libsql (klien Turso)
        if TURSO_TOKEN:
            conn = libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)
        else:
            conn = libsql.connect(TURSO_URL)  # file: lokal, tanpa token
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass  # tidak semua endpoint remote mengizinkan PRAGMA
        return _Connection(conn)
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def now():
    return int(time.time())


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False)


def jload(s, default=None):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default
