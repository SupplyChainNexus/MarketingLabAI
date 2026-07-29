"""Tests for the MarketingLabAI CLI router."""

import unittest
from argparse import Namespace
from unittest.mock import patch

from app.main import build_parser, run_command


class MainCliTests(unittest.TestCase):
    def test_parser_accepts_onboard_command(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["onboard"])

        self.assertEqual(args.command, "onboard")

    @patch("app.main.run_onboarding")
    def test_onboard_command_runs_workflow(
        self,
        mocked_onboarding,
    ) -> None:
        args = Namespace(command="onboard")

        run_command(args)

        mocked_onboarding.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
