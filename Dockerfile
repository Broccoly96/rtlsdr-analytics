# Shared image for adsb-collector and adsb-api (PLAN.md SS6.1: "collector
# and API may share an image on small servers, but keep the
# processes/responsibilities separate" -- the actual process run is chosen
# per-service via compose.yaml's `command:`).
#
# Installed with `pip install -e .` (not a full site-packages install) so
# app/version.py's pyproject.toml lookup (relative to its own file location)
# keeps working the same way it does in local dev -- the source tree stays
# at /app rather than being copied elsewhere.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY scripts ./scripts

RUN pip install --no-cache-dir -e . \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

# Baked in at build time (compose.yaml's build.args) since the running
# container has neither a .git directory (.dockerignore excludes it) nor
# a `git` binary -- app/version.py's get_git_revision() reads this env
# var first, falling back to a live `git` subprocess that only works in
# a local (non-container) checkout.
ARG GIT_REVISION=unknown
ENV GIT_REVISION=$GIT_REVISION

USER appuser
