"""ASGI entrypoint for uvicorn: `uvicorn app.api.asgi:app`.

Constructing Settings() (and therefore this module) at import time fails
fast with a clear message on misconfiguration, matching the collector
entrypoint's startup-failure behavior.
"""

import logging

from app.api.main import create_app

# Matches the collector/retention entrypoints' format (PLAN.md SS8 E-4:
# consistent structured logging across services) -- without this, app-level
# loggers (e.g. app/api/errors.py) would fall through to Python's unconfigured
# lastResort handler and look different from the other two services' logs.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = create_app()
