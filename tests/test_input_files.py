"""Tests for workflow input-file utilities."""

import json
import tempfile
import unittest
from pathlib import Path

from app.services.input_files import (
    read_json_file,
    read_writing_samples,
)


class InputFileTests(unittest.TestCase):

    def test_reads_json_object(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brand.json"

            path.write_text(
                json.dumps(
                    {
                        "brand_id": "brand-1",
                        "name": "Test Brand",
                    }
                ),
                encoding="utf-8",
            )

            data = read_json_file(path)

            self.assertEqual(
                data["brand_id"],
                "brand-1",
            )

    def test_rejects_json_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            path.write_text(
                "[]",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                read_json_file(path)

    def test_reads_multiple_writing_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samples.txt"

            path.write_text(
                "Sample one.\n---\nSample two.",
                encoding="utf-8",
            )

            samples = read_writing_samples(path)

            self.assertEqual(
                samples,
                ["Sample one.", "Sample two."],
            )


if __name__ == "__main__":
    unittest.main()
