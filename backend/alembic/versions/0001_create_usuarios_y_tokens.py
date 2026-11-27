"""crear tablas usuarios y tokens

Revision ID: 0001
Revises:
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("rol", sa.String(length=32), nullable=False, server_default="cliente"),
        sa.Column(
            "estado",
            sa.String(length=32),
            nullable=False,
            server_default="pendiente_activacion",
        ),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)

    op.create_table(
        "tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("expira_en", sa.DateTime(), nullable=False),
        sa.Column("usado_en", sa.DateTime(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tokens_token_hash", "tokens", ["token_hash"], unique=False)
    op.create_index("ix_tokens_usuario_id", "tokens", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tokens_usuario_id", table_name="tokens")
    op.drop_index("ix_tokens_token_hash", table_name="tokens")
    op.drop_table("tokens")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
