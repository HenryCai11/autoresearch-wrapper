#!/usr/bin/env python3

from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "autoresearch-wrapper"

SYNC_TARGETS = {
    # skills/ is the single source for Claude Code and Codex; .claude/skills and
    # .agents/skills are symlinks to it, and the plugin ships a real copy.
    REPO_ROOT / "skills": PLUGIN_ROOT / "skills",
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


# The root SKILL.md lets the repo itself be installed as one skill (and is what skill
# indexes read first). It is a generated copy of the main skill, never edited by hand.
ROOT_SKILL_SOURCE = REPO_ROOT / "skills" / "autoresearch-wrapper" / "SKILL.md"
ROOT_SKILL_COPY = REPO_ROOT / "SKILL.md"


def main() -> int:
    PLUGIN_ROOT.mkdir(parents=True, exist_ok=True)
    for source, destination in SYNC_TARGETS.items():
        copy_tree(source, destination)
        print(f"synced {source.relative_to(REPO_ROOT)} -> {destination.relative_to(REPO_ROOT)}")
    shutil.copyfile(ROOT_SKILL_SOURCE, ROOT_SKILL_COPY)
    print(f"synced {ROOT_SKILL_SOURCE.relative_to(REPO_ROOT)} -> {ROOT_SKILL_COPY.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
