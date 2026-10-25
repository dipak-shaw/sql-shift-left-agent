from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DiffChunk:
    file_path: str
    start_line: int
    end_line: int
    content: str


def extract_changed_lines(diff_text: str) -> list[DiffChunk]:
    chunks: list[DiffChunk] = []
    current_path: Optional[str] = None
    start_line = 1
    current_lines: list[str] = []

    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            current_path = line[6:]
        elif line.startswith("@@"):
            if current_path:
                target = line.split("+")[-1].split(",")[0]
                start_line = int(target) if target.isdigit() else 1
                current_lines = []
        elif line.startswith("+") and not line.startswith("+++"):
            current_lines.append(line[1:])
            chunks.append(
                DiffChunk(
                    file_path=current_path or "unknown",
                    start_line=start_line,
                    end_line=start_line + len(current_lines) - 1,
                    content="\n".join(current_lines),
                )
            )
            start_line += 1
    return chunks
