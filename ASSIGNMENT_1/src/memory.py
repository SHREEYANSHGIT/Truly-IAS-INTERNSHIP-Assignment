"""Short-term conversation memory for follow-up questions.

A lightweight, dependency-free sliding-window memory that keeps the last
``MEMORY_K`` turns so the bot can resolve pronouns and references in follow-up
questions (e.g. *"What about for premium accounts?"*).
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

from src import config

logger = logging.getLogger(__name__)


@dataclass
class ConversationMemory:
    """Sliding-window buffer of past human/ai turns."""

    k: int = field(default_factory=lambda: config.MEMORY_K)
    _turns: deque = field(default_factory=deque)

    def add(self, role: str, content: str) -> None:
        """Append a turn and trim to the last ``k`` entries."""
        self._turns.append({"role": role, "content": content})
        while len(self._turns) > self.k:
            self._turns.popleft()

    def to_history(self) -> list[dict[str, str]]:
        """Return the buffered turns as ``{"role", "content"}`` dicts."""
        return list(self._turns)

    def clear(self) -> None:
        """Reset the conversation memory."""
        self._turns.clear()


def create_memory() -> ConversationMemory:
    """Return a fresh conversation-memory buffer."""
    memory = ConversationMemory()
    logger.info("Created conversation memory (k=%d)", config.MEMORY_K)
    return memory
