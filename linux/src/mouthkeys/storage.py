import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .config import private_dir, state_dir


class History:
    """Private local history. Audio is retained only for failures and the latest recording."""

    def __init__(self, root: Path | None = None):
        self.root = private_dir(root or state_dir())
        self.audio = private_dir(self.root / "recordings")
        self.db = self.root / "history.sqlite3"
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS history (
                id TEXT PRIMARY KEY, created REAL NOT NULL, text TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '')""")
        self.db.chmod(0o600)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db, timeout=3)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def begin(self, item_id: str):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO history(id, created, status) VALUES (?, ?, 'recording')",
                (item_id, time.time()),
            )

    def update(self, item_id: str, status: str, text: str = "", error: str = ""):
        with self.connect() as conn:
            conn.execute(
                "UPDATE history SET status=?, text=?, error=? WHERE id=?",
                (status, text, error, item_id),
            )

    def rows(self, limit=100):
        with self.connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT * FROM history ORDER BY created DESC LIMIT ?", (limit,)
                )
            ]

    def latest_text(self):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT text FROM history WHERE text != '' ORDER BY created DESC LIMIT 1"
            ).fetchone()
        if row is None:
            raise ValueError("No transcript yet")
        return row["text"]

    def recover(self):
        with self.connect() as conn:
            conn.execute("""UPDATE history SET status='failed', error='Interrupted; reprocess audio'
                WHERE status IN ('recording', 'transcribing')""")

    def prune_audio(self, keep: str):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id FROM history WHERE status IN "
                "('copied', 'paste_requested', 'transcribed', 'cancelled')"
            )
            for row in rows:
                if row["id"] != keep:
                    self.recording(row["id"]).unlink(missing_ok=True)

    def recording(self, item_id: str):
        # IDs arrive over IPC; never let a history request escape the recordings directory.
        import uuid

        return self.audio / f"{uuid.UUID(item_id)}.wav"

    def clear(self):
        with self.connect() as conn:
            conn.execute("DELETE FROM history")
        for path in self.audio.glob("*.wav"):
            path.unlink()
