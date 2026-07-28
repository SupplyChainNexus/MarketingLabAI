"""Tests for Voice Engine response parsing."""

import unittest

from app.voices.voice_engine import VoiceEngine


class VoiceParsingTests(unittest.TestCase):

    def test_parses_plain_json(self):
        response = """
        {
          "summary": "Clear",
          "tone_traits": ["direct"],
          "preferred_words": [],
          "avoided_words": [],
          "sentence_style": "Short",
          "call_to_action_style": "Direct",
          "authenticity_rules": []
        }
        """

        data = VoiceEngine.parse_analysis_response(response)

        self.assertEqual(
            data["summary"],
            "Clear",
        )

    def test_parses_markdown_json_fence(self):
        response = """```json
{
  "summary": "Helpful"
}
```"""

        data = VoiceEngine.parse_analysis_response(response)

        self.assertEqual(
            data["summary"],
            "Helpful",
        )

    def test_validation_detects_missing_fields(self):
        with self.assertRaises(RuntimeError):
            VoiceEngine.validate_analysis_data({"summary": "Incomplete"})


if __name__ == "__main__":
    unittest.main()
