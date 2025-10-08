"""Prompt pool helpers for sampling unique combinations."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence, Set


@dataclass
class PromptPool:
    """Maintain prompt candidates and support deduplicated sampling."""

    texts: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    _used_hashes: Set[str] = field(default_factory=set, init=False, repr=False)

    @classmethod
    def from_file(cls, path: Path) -> "PromptPool":
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return cls(texts=lines)

    def extend_texts(self, values: Iterable[str]) -> None:
        self.texts.extend(filter(None, map(str.strip, values)))

    def extend_styles(self, values: Iterable[str]) -> None:
        self.styles.extend(filter(None, map(str.strip, values)))

    def extend_tags(self, values: Iterable[str]) -> None:
        self.tags.extend(filter(None, map(str.strip, values)))

    def clear_usage(self) -> None:
        self._used_hashes.clear()

    def random_choice(self, count: int = 1) -> List[str]:
        if not self.texts:
            raise ValueError("PromptPool has no text entries")
        return random.sample(self.texts, k=min(count, len(self.texts)))

    def sample_combo(self) -> str:
        """Combine text, style and tags with deduplication."""

        text = random.choice(self.texts) if self.texts else ""
        style = random.choice(self.styles) if self.styles else ""
        tag_list = random.sample(self.tags, k=min(len(self.tags), 3)) if self.tags else []

        parts: Sequence[str] = [text, style, ", ".join(tag_list)]
        combo = " | ".join(filter(None, parts))
        combo_hash = combo.lower()

        attempts = 0
        while combo_hash in self._used_hashes and attempts < 5:
            text = random.choice(self.texts)
            style = random.choice(self.styles) if self.styles else style
            tag_list = random.sample(self.tags, k=min(len(self.tags), 3)) if self.tags else tag_list
            parts = [text, style, ", ".join(tag_list)]
            combo = " | ".join(filter(None, parts))
            combo_hash = combo.lower()
            attempts += 1

        self._used_hashes.add(combo_hash)
        return combo


__all__ = ["PromptPool"]
