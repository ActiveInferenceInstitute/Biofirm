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
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SKIP_PARTS = {".git", ".venv", "artifacts", "Outputs", "Visualizations", "__pycache__"}


def main() -> int:
    if not compileall.compile_dir(str(ROOT / "src"), quiet=1):
        return 1
    sys.path.insert(0, str(ROOT / "src"))
    import biofirm
    from biofirm.data_validation import validate_repository_data

    if not biofirm.__version__:
        print("biofirm.__version__ is empty", file=sys.stderr)
        return 1
    for required_document in (
        ROOT / "README.md",
        ROOT / "Biofirm_Generative_Model.md",
        ROOT / "CONFIGURATION.md",
        ROOT / "TODO.md",
        ROOT / "DOCUMENTATION_INDEX.md",
        ROOT / "One_Earth" / "INSTALLATION_GUIDE.md",
        ROOT / "GNN.md",
    ):
        if (
            not required_document.is_file()
            or not required_document.read_text(encoding="utf-8").strip()
        ):
            print(
                f"required documentation is missing or empty: {required_document}", file=sys.stderr
            )
            return 1
    for document in ROOT.rglob("*.md"):
        if any(part in SKIP_PARTS for part in document.parts):
            continue
        text = document.read_text(encoding="utf-8", errors="ignore")
        for target in MARKDOWN_LINK_PATTERN.findall(text):
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative_target = target.split("#", 1)[0]
            if relative_target and not (document.parent / relative_target).exists():
                print(f"broken local link in {document}: {target}", file=sys.stderr)
                return 1
    try:
        validate_repository_data(
            one_earth_path=ROOT / "One_Earth" / "oneearth_bioregion_ecoregions.json",
            biofirm_regions_path=ROOT / "Bio_Perplexity" / "Biofirm_Regions.json",
            california_regions_path=ROOT / "Bio_Perplexity" / "CA_Biofirm_Regions.json",
            biofirm_prompts_path=ROOT / "Bio_Perplexity" / "Biofirm_System_Prompts.json",
            one_earth_prompts_path=ROOT / "One_Earth" / "OneEarth_System_Prompts.json",
        )
    except ValueError as exc:
        print(f"source data validation failed: {exc}", file=sys.stderr)
        return 1
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
