"""crear despacho: asignacion de motorizado e historial de estados

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pedidos", sa.Column("motorizado_id", sa.BigInteger(), nullable=True))
    op.add_column("pedidos", sa.Column("asignado_en", sa.DateTime(), nullable=True))
    op.create_index("ix_pedidos_motorizado_id", "pedidos", ["motorizado_id"])
    op.create_foreign_key(
        "fk_pedidos_motorizado",
        "pedidos",
        "usuarios",
        ["motorizado_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "pedido_estado_historial",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.BigInteger(), nullable=False),
        sa.Column("estado_anterior", sa.String(length=32), nullable=True),
        sa.Column("estado_nuevo", sa.String(length=32), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pedido_estado_historial_pedido_id",
        "pedido_estado_historial",
        ["pedido_id"],
    )
    op.create_index(
        "ix_pedido_estado_historial_creado_en",
        "pedido_estado_historial",
        ["creado_en"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pedido_estado_historial_creado_en", table_name="pedido_estado_historial"
    )
    op.drop_index(
        "ix_pedido_estado_historial_pedido_id", table_name="pedido_estado_historial"
    )
    op.drop_table("pedido_estado_historial")
    op.drop_constraint("fk_pedidos_motorizado", "pedidos", type_="foreignkey")
    op.drop_index("ix_pedidos_motorizado_id", table_name="pedidos")
    op.drop_column("pedidos", "asignado_en")
    op.drop_column("pedidos", "motorizado_id")
