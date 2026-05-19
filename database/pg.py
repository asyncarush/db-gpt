from contextlib import contextmanager
from typing import Optional
from agent.config import Config
from logging import getLogger

log = getLogger(__name__)

config = Config()

import psycopg2
from psycopg2.extras import RealDictCursor


class DatabaseError(RuntimeError):
    """Raised on unrecoverable database failures."""


class Database:
    def __init__(self, config: Config):
        self._config = config
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._connect()

    # -- Connection management ------------------------------------------------

    def _connect(self):
        log.info("Connecting to database …")
        self._conn = psycopg2.connect(self._config.db_uri)
        self._conn.autocommit = True
        log.info("Database connection established.")

    def _ensure_connected(self):
        """Reconnect automatically if the connection was dropped."""
        try:
            self._conn.cursor().execute("SELECT 1")
        except Exception:
            log.warning("Database connection lost — reconnecting …")
            self._connect()

    @contextmanager
    def cursor(self):
        self._ensure_connected()
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cur
        except psycopg2.Error as exc:
            log.error("Database error: %s", exc)
            raise DatabaseError(str(exc)) from exc
        finally:
            cur.close()

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
            log.info("Database connection closed.")

db = Database(config)
