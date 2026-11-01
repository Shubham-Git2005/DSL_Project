import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                status TEXT NOT NULL, payload TEXT NOT NULL,
                report TEXT, error TEXT, review_note TEXT)""")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def insert(self, key, timestamp, payload):
        with self.connect() as db:
            db.execute("INSERT INTO assessments (id,created_at,status,payload) VALUES (?,?,?,?)",
                       (key, timestamp, "queued", json.dumps(payload)))

    def update(self, key, *, status=None, report=None, error=None, review_note=None):
        values = {"status": status, "report": json.dumps(report) if report is not None else None,
                  "error": error, "review_note": review_note}
        values = {k: v for k, v in values.items() if v is not None}
        if not values:
            return
        with self.connect() as db:
            db.execute(f"UPDATE assessments SET {','.join(k+'=?' for k in values)} WHERE id=?",
                       [*values.values(), key])

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT * FROM assessments WHERE id=?", (key,)).fetchone()
        if not row:
            return None
        item = dict(row)
        for field in ["payload", "report"]:
            item[field] = json.loads(item[field]) if item[field] else None
        return item

    def list(self):
        with self.connect() as db:
            rows = db.execute("SELECT id,created_at,status,payload,review_note FROM assessments ORDER BY created_at DESC LIMIT 100").fetchall()
        return [{"id": r["id"], "created_at": r["created_at"], "status": r["status"],
                 "student_name": json.loads(r["payload"])["student_name"],
                 "target_role": json.loads(r["payload"])["target_role"],
                 "review_requested": bool(r["review_note"])} for r in rows]

    def delete(self, key):
        with self.connect() as db:
            return db.execute("DELETE FROM assessments WHERE id=?", (key,)).rowcount

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE assessments SET status='failed',error='Server restarted during assessment. Submit again.' WHERE status IN ('queued','processing')")
