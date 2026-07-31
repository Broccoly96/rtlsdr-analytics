"""Application version: read from pyproject.toml (single source of truth)
plus the current git commit if available. Exposed via /api/config and shown
in the dashboard footer, mainly so it's possible to confirm which exact
build a running instance (e.g. a remote preview) is actually serving.

pyproject.toml's version is the only one of the two guaranteed to reach
production -- see CLAUDE.md's Versioning section for the bump policy this
depends on. The git commit suffix is best-effort: real in a deployed
container only when built with `GIT_REVISION=$(git rev-parse --short HEAD)`
(see compose.yaml/Dockerfile), otherwise falls back to a live `git`
subprocess call that only works in a local checkout.
"""

from __future__ import annotations

import os
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
    """Prefers the GIT_REVISION env var, baked into the image at build time
    (Dockerfile's ARG/ENV, populated from compose.yaml's build.args) --
    a built container has no .git directory (.dockerignore excludes it)
    and no `git` binary (python:3.12-slim), so the subprocess fallback
    below always returned None there before this env var existed. The
    subprocess path is kept for local/dev checkouts, where .git and `git`
    both genuinely exist and this already worked."""
    env_revision = os.environ.get("GIT_REVISION", "").strip()
    if env_revision and env_revision != "unknown":
        return env_revision
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
