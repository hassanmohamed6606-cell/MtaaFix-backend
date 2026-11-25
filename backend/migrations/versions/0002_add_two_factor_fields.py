
"""Add two-factor authentication fields to users.

Revision ID: 0002_add_two_factor
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_two_factor"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "totp_secret_encrypted",
            sa.String(length=512),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "totp_last_counter",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "recovery_codes_hashes",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("users", "recovery_codes_hashes")
    op.drop_column("users", "totp_last_counter")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_encrypted")
