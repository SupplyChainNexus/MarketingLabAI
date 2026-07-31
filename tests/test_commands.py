"""Tests for the application command layer."""

from __future__ import annotations

import unittest

from app.commands.base import Command


class ExampleCommand(Command[int]):
    def execute(self) -> int:
        return 42


class CommandTests(unittest.TestCase):
    def test_command_returns_expected_result(self) -> None:
        command = ExampleCommand()

        self.assertEqual(
            command.execute(),
            42,
        )

    def test_command_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            Command()


if __name__ == "__main__":
    unittest.main()
