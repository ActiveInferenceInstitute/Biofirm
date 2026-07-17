"""Atomic, non-empty JSON and text artifact writers."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any


class ArtifactError(ValueError):
    """Raised when an artifact cannot be written as a complete non-empty file."""


def atomic_write_text(path: str | Path, value: str) -> Path:
    """Write text through a same-directory temporary file and atomic replacement."""

    if not isinstance(value, str) or not value.strip():
        raise ArtifactError("artifact text must be a non-empty string")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(value)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, destination)
    except OSError as exc:
        if temporary_name is not None:
            with suppress(OSError):
                os.unlink(temporary_name)
        raise ArtifactError(f"could not atomically write {destination}") from exc
    if not destination.is_file() or destination.stat().st_size == 0:
        raise ArtifactError(f"artifact {destination} is empty after writing")
    return destination


def atomic_write_json(path: str | Path, value: Mapping[str, Any] | list[Any]) -> Path:
    """Serialize JSON without NaN values, then atomically write a non-empty artifact."""

    try:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ArtifactError("artifact value is not valid JSON") from exc
    return atomic_write_text(path, text + "\n")
