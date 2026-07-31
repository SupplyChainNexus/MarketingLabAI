"""Base class for application commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

ResultT = TypeVar("ResultT")


class Command(ABC, Generic[ResultT]):
    """Base class for application commands."""

    @abstractmethod
    def execute(self) -> ResultT:
        """Execute the command."""
