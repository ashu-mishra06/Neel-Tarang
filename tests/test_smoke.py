"""Level 0 smoke tests: repo layout and no-secrets check."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [re.compile(r"sk-[A-Za-z0-9_-]{16,}"), re.compile(r"API_KEY=[A-Za-z0-9_-]{8,}")]
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
TEXT_SUFFIXES = {".py", ".txt", ".md", ".toml", ".yaml", ".yml", ".csv", ".j2", ".json", ""}


def test_scoring_package_imports() -> None:
    import scoring  # noqa: F401


def test_required_files_exist() -> None:
    for name in ["LICENSE", "README.md", "requirements.txt", ".env.example", ".gitignore"]:
        assert (ROOT / name).is_file(), name


def test_no_secrets_in_repo() -> None:
    hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or SKIP_DIRS & set(path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES or path.name == ".env":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        hits += [f"{path.name}: {p.pattern}" for p in SECRET_PATTERNS if p.search(text)]
    assert not hits, hits
