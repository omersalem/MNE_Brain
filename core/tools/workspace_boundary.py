"""Path, traversal, symlink, and protected-file enforcement for workspace tools."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Iterable


class WorkspaceBoundaryError(PermissionError):
    pass


class WorkspaceBoundary:
    def __init__(self, root: Path, protected_paths: Iterable[str]):
        self.root = root.resolve()
        self.protected = {PurePosixPath(item.replace("\\", "/")).as_posix().strip("/") for item in protected_paths}

    def _relative_text(self, value: str | Path) -> str:
        raw = str(value).replace("\\", "/")
        if re.search(r"[*?\[\]{}!|;&`$<>:]", raw):
            raise WorkspaceBoundaryError("Wildcard, command, and stream path syntax is rejected.")
        pure = PurePosixPath(raw)
        if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
            raise WorkspaceBoundaryError("Absolute paths and traversal are rejected.")
        return pure.as_posix()

    def is_protected(self, value: str | Path) -> bool:
        relative = self._relative_text(value)
        return any(relative == item or relative.startswith(item + "/") for item in self.protected)

    def resolve(self, value: str | Path, *, for_write: bool = False) -> Path:
        relative = self._relative_text(value)
        if self.is_protected(relative):
            raise WorkspaceBoundaryError("Protected workspace path rejected.")
        candidate = self.root / Path(relative)
        probe = candidate if candidate.exists() else candidate.parent
        probe_resolved = probe.resolve()
        try:
            probe_resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceBoundaryError("Workspace path escaped the approved root.") from exc
        current = self.root
        for part in Path(relative).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise WorkspaceBoundaryError("Symlink paths are rejected.")
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceBoundaryError("Workspace path escaped the approved root.") from exc
        return candidate

    def parse_diff_paths(self, unified_diff: str) -> list[str]:
        paths: list[str] = []
        for line in unified_diff.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                raw = line[4:].split("\t", 1)[0].strip()
                if raw == "/dev/null":
                    continue
                if raw.startswith(("a/", "b/")):
                    raw = raw[2:]
                relative = self._relative_text(raw)
                self.resolve(relative, for_write=True)
                if relative not in paths:
                    paths.append(relative)
        if not paths:
            raise WorkspaceBoundaryError("Unified diff contains no valid paths.")
        return paths
