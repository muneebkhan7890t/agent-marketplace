"""
services/email_memory.py
------------------------
Tracks which email IDs have already been processed to prevent duplicate replies.
Uses a JSON file as a simple persistent store.

For production at scale: replace with a Redis SET or a DB table.
"""

import json
import os

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "processed_emails.json")


class EmailMemory:

    def __init__(self, filepath: str = None):
        self.filepath = filepath or os.path.abspath(MEMORY_FILE)
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w") as f:
                json.dump([], f)

    def _load(self) -> list:
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save(self, ids: list):
        with open(self.filepath, "w") as f:
            json.dump(ids, f, indent=2)

    def is_processed(self, email_id: str) -> bool:
        return email_id in self._load()

    def mark_processed(self, email_id: str):
        ids = self._load()
        if email_id not in ids:
            ids.append(email_id)
            self._save(ids)

    def clear(self):
        """Reset memory (useful for testing)."""
        self._save([])

    def count(self) -> int:
        return len(self._load())
