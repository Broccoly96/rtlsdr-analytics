"""add favorites

Revision ID: 50bcdde414ab
Revises: d6494c2713c8
Create Date: 2026-08-01 04:11:59.417923

Milestone JJ of the 2026-08 feature roadmap: favorites move from
client-only localStorage (app/static/js/history.js's previous
"deliberately zero backend" design) to a real, server-side, persisted
record -- the app's first mutating (POST/DELETE) endpoints, a deliberate
exception to the otherwise all-GET/unauthenticated API surface (see
CLAUDE.md), justified by this app being tailnet-only/single-user by
design. `added_at` exists for potential future sorting/display; there's
no `removed_at`/soft-delete -- unfavoriting just deletes the row, same
as the localStorage version's array splice.

Hand-written raw SQL, following 62c3f8022564/5cee58fd601d/d6494c2713c8's
precedent. Downgrade policy: same fix-forward-only stance -- safe against
an empty/test database only.
"""

from alembic import op

revision: str = "50bcdde414ab"
down_revision: str | None = "d6494c2713c8"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE favorites (
            icao        TEXT PRIMARY KEY REFERENCES aircraft (icao),
            added_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE favorites")
