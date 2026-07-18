"""Deterministic visualization with explicit optional dependency contracts."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Iterable
from contextlib import suppress
from pathlib import Path


class VisualizationDependencyError(RuntimeError):
    """Raised when visualization was requested without its documented extras."""


def deterministic_tokens(text: str) -> list[str]:
    """Tokenize text with a stable standard-library rule; spaCy is not required."""

    import re

    return re.findall(r"[\w'-]+", text.lower(), flags=re.UNICODE)


def visualize_documents(
    texts: Iterable[str],
    labels: Iterable[str],
    output: str | Path,
    *,
    seed: int = 7,
) -> Path:
    """Create a non-empty deterministic TF-IDF/PCA scatter plot."""

    text_values = list(texts)
    label_values = list(labels)
    if not text_values or len(text_values) != len(label_values):
        raise ValueError("texts and labels must be non-empty and have equal length")
    if any(not isinstance(text, str) or not text.strip() for text in text_values):
        raise ValueError("texts must contain non-empty strings")
    if any(not isinstance(label, str) or not label.strip() for label in label_values):
        raise ValueError("labels must contain non-empty strings")
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.decomposition import PCA
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError as exc:
        raise VisualizationDependencyError(
            "visualization requires matplotlib and scikit-learn; install biofirm[visualization]"
        ) from exc
    vectorizer = TfidfVectorizer(
        tokenizer=deterministic_tokens, token_pattern=None, lowercase=False
    )
    matrix = vectorizer.fit_transform(text_values).toarray()
    if matrix.shape[1] == 0:
        raise ValueError("documents contain no tokens")
    if len(text_values) == 1:
        points = [[0.0, 0.0]]
    elif matrix.shape[1] == 1:
        points = [[float(value), 0.0] for value in matrix[:, 0]]
    else:
        components = min(2, matrix.shape[0], matrix.shape[1])
        reduced = PCA(n_components=components, random_state=seed).fit_transform(matrix)
        points = [[float(row[0]), float(row[1]) if components > 1 else 0.0] for row in reduced]
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    figure, axis = plt.subplots(figsize=(8, 5), constrained_layout=True)
    try:
        for point, label in zip(points, label_values, strict=True):
            color = f"#{hashlib.sha256(label.encode('utf-8')).hexdigest()[:6]}"
            axis.scatter(point[0], point[1], color=color, s=70, label=label)
            axis.annotate(
                label, (point[0], point[1]), textcoords="offset points", xytext=(4, 4), fontsize=8
            )
        axis.set_title("Biofirm document embedding")
        axis.set_xlabel("principal component 1")
        axis.set_ylabel("principal component 2")
        if len(set(label_values)) <= 12:
            axis.legend(loc="best", fontsize=8)
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False
        ) as temporary:
            temporary_name = temporary.name
        output_format = destination.suffix.lstrip(".") or "png"
        figure.savefig(temporary_name, dpi=150, format=output_format)
        if Path(temporary_name).stat().st_size == 0:
            raise RuntimeError("visualization produced an empty artifact")
        os.replace(temporary_name, destination)
        temporary_name = None
    finally:
        plt.close(figure)
        if temporary_name is not None:
            with suppress(OSError):
                os.unlink(temporary_name)
    return destination
