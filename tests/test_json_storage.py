"""Tests for JSON storage."""

import tempfile
import unittest
from pathlib import Path

from app.services.json_storage import JsonStorage


class JsonStorageTests(unittest.TestCase):

    def test_save_and_load_record(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = JsonStorage(Path(directory))

            storage.save(
                "record-1",
                {"name": "MarketingLabAI"},
            )

            loaded = storage.load("record-1")

            self.assertEqual(
                loaded["name"],
                "MarketingLabAI",
            )

    def test_list_records(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = JsonStorage(Path(directory))

            storage.save("brand-b", {"name": "B"})
            storage.save("brand-a", {"name": "A"})

            self.assertEqual(
                storage.list_records(),
                ["brand-a", "brand-b"],
            )

    def test_rejects_invalid_record_id(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = JsonStorage(Path(directory))

            with self.assertRaises(ValueError):
                storage.save("../unsafe", {"value": True})


if __name__ == "__main__":
    unittest.main()
