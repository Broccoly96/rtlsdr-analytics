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

USER appuser
