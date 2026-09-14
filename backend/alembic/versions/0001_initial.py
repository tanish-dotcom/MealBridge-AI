"""Initial schema (portable; works on SQLite and PostgreSQL)."""
from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from app.models import Base

    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    from app.models import Base

    Base.metadata.drop_all(bind=bind)