"""Repository syntax, import, notebook, and credential checks."""

from __future__ import annotations

import compileall
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(?:openai|perplexity|anthropic)[ _-]?api[ _-]?key\s*[:=]\s*['\"]?\w{20,}"),
)
SKIP_PARTS = {".git", ".venv", "artifacts", "Outputs", "Visualizations", "__pycache__"}


def main() -> int:
    if not compileall.compile_dir(str(ROOT / "src"), quiet=1):
        return 1
    sys.path.insert(0, str(ROOT / "src"))
    import biofirm

    assert biofirm.__version__
    for notebook in (ROOT / "Documentation" / "Notebooks").glob("*.ipynb"):
        try:
            import nbformat

            parsed = nbformat.read(notebook, as_version=4)
            for index, cell in enumerate(parsed.cells):
                if cell.cell_type != "code":
                    continue
                for line in cell.source.splitlines():
                    if line.lstrip().startswith(("!", "%")):
                        print(
                            f"notebook cell {notebook}:{index} contains a shell or magic command",
                            file=sys.stderr,
                        )
                        return 1
        except ImportError:
            break
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in {
            ".py",
            ".json",
            ".md",
            ".toml",
            ".yml",
            ".yaml",
            ".ipynb",
            ".env",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in SECRET_PATTERNS):
            print(f"credential pattern found in {path}", file=sys.stderr)
            return 1
    print("repository checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
