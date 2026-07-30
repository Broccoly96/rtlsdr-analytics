"""Application version: read from pyproject.toml (single source of truth)
plus the current git commit if available. Exposed via /api/config and shown
in the dashboard footer, mainly so it's possible to confirm which exact
build a running instance (e.g. a remote preview) is actually serving.
"""

from __future__ import annotations

import subprocess
import tomllib
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"


@lru_cache(maxsize=1)
def get_version() -> str:
    try:
        with _PYPROJECT_PATH.open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "unknown"


@lru_cache(maxsize=1)
def get_user_agent() -> str:
    """Descriptive User-Agent for outbound calls to third-party APIs
    (api.adsbdb.com, api.planespotters.net) -- some of them (Planespotters)
    explicitly reject generic library/browser User-Agent strings and
    require a descriptive one with a contact URL. A browser's own fetch()
    can't override its User-Agent at all (forbidden header), which is
    exactly why the photo lookup is a server-side proxy rather than a
    direct browser call -- see app/api/routers/aircraft_history.py."""
    return f"rtlsdr-analytics/{get_version()} (+https://github.com/Broccoly96/rtlsdr-analytics)"


@lru_cache(maxsize=1)
def get_git_revision() -> str | None:
    """None in environments with no .git directory (e.g. a built container
    image, since .dockerignore excludes .git/) -- that's expected."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None
