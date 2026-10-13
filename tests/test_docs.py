"""Documentation numbers that must follow the pinned manifest."""

from __future__ import annotations

import re

from common import ROOT, load_release


def test_readme_group_sizes_match_the_manifest():
    release = load_release()
    readme = (ROOT / "README.md").read_text()
    for group in ("listing", "engineer", "researcher", "all"):
        tables = release.group(group)
        row = re.search(rf"^\| `{group}` \| (\d+) \| ([\d,]+) bytes", readme, re.MULTILINE)
        assert row, f"no README row for {group}"
        assert int(row.group(1)) == len(tables)
        assert int(row.group(2).replace(",", "")) == release.size(tables)


def test_no_developer_paths_in_tracked_text():
    home = "Users"  # split so this file does not match itself
    pattern = re.compile(rf"/{home}/|/home/[a-z]|C:\\\\{home}")
    for path in ROOT.rglob("*"):
        if any(part in {".git", ".venv", "data", "outputs", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.is_file() and path.suffix in {".py", ".sql", ".md", ".json", ".yaml", ".yml", ".toml", ".cff", ".csv"}:
            assert not pattern.search(path.read_text(encoding="utf-8")), path
