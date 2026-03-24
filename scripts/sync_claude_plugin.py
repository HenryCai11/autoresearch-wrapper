#!/usr/bin/env python3

from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "autoresearch-wrapper"

SYNC_TARGETS = {
    REPO_ROOT / ".claude" / "skills": PLUGIN_ROOT / "skills",
    REPO_ROOT / "scripts": PLUGIN_ROOT / "scripts",
    REPO_ROOT / "autoresearch_wrapper": PLUGIN_ROOT / "autoresearch_wrapper",
    REPO_ROOT / "templates": PLUGIN_ROOT / "templates",
}


def reset_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def copy_tree(source: Path, destination: Path) -> None:
    reset_path(destination)
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def main() -> int:
    PLUGIN_ROOT.mkdir(parents=True, exist_ok=True)
    for source, destination in SYNC_TARGETS.items():
        copy_tree(source, destination)
        print(f"synced {source.relative_to(REPO_ROOT)} -> {destination.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
