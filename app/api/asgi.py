"""ASGI entrypoint for uvicorn: `uvicorn app.api.asgi:app`.

Constructing Settings() (and therefore this module) at import time fails
fast with a clear message on misconfiguration, matching the collector
entrypoint's startup-failure behavior.
"""

from app.api.main import create_app

app = create_app()
