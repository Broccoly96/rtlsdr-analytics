"""Makes the ephemeral-Postgres fixtures available to every test under
tests/ (tests/contract/ and tests/integration/) without per-file imports."""

from tests.contract.pg_container import clean_db, postgres_url  # noqa: F401
