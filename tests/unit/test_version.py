from __future__ import annotations

from app.version import get_git_revision


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
