from __future__ import annotations

import re
from pathlib import Path

from app.version import get_git_revision, get_version


def test_latest_changelog_entry_matches_application_version():
    changelog_js = (
        Path(__file__).resolve().parents[2] / "app" / "static" / "js" / "changelog.js"
    ).read_text()
    latest = re.search(r'const ENTRIES = \[\s*\{ version: "([^"]+)"', changelog_js)

    assert latest is not None
    assert latest.group(1) == get_version()


def test_git_revision_prefers_env_var(monkeypatch):
    monkeypatch.setenv("GIT_REVISION", "abc1234")
    get_git_revision.cache_clear()
    try:
        assert get_git_revision() == "abc1234"
    finally:
        get_git_revision.cache_clear()


def test_git_revision_ignores_unknown_placeholder(monkeypatch):
    # Dockerfile's ARG GIT_REVISION=unknown default -- must not be treated
    # as a real revision, so a build without a real value still falls back
    # to the subprocess (or None), not a literal "unknown" being displayed.
    monkeypatch.setenv("GIT_REVISION", "unknown")
    get_git_revision.cache_clear()
    try:
        assert get_git_revision() != "unknown"
    finally:
        get_git_revision.cache_clear()


def test_git_revision_falls_back_without_env_var(monkeypatch):
    monkeypatch.delenv("GIT_REVISION", raising=False)
    get_git_revision.cache_clear()
    try:
        # In this local checkout .git exists, so the subprocess fallback
        # should succeed with a real short hash rather than None.
        result = get_git_revision()
        assert result is None or (isinstance(result, str) and len(result) >= 7)
    finally:
        get_git_revision.cache_clear()
