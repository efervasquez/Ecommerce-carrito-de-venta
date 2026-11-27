"""crear sesiones, carritos e inventario local

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sesiones",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("expira_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sesiones_usuario_id", "sesiones", ["usuario_id"])
    op.create_index("ix_sesiones_ip_address", "sesiones", ["ip_address"])

    op.create_table(
        "carritos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sesion_id", sa.String(length=64), nullable=False),
        sa.Column("estado", sa.String(length=24), nullable=False, server_default="activo"),
        sa.Column("reserva_expira_en", sa.DateTime(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sesion_id"], ["sesiones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sesion_id"),
    )

    op.create_table(
        "carrito_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("carrito_id", sa.BigInteger(), nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("cantidad_reservada", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("descuento_porcentaje", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["carrito_id"], ["carritos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("carrito_id", "producto_id", name="uq_carrito_producto"),
    )
    op.create_index("ix_carrito_items_carrito_id", "carrito_items", ["carrito_id"])
    op.create_index("ix_carrito_items_producto_id", "carrito_items", ["producto_id"])

    op.create_table(
        "inventario_stock",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("disponible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reservado", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("producto_id"),
    )
    op.create_index("ix_inventario_stock_producto_id", "inventario_stock", ["producto_id"])


def downgrade() -> None:
    op.drop_index("ix_inventario_stock_producto_id", table_name="inventario_stock")
    op.drop_table("inventario_stock")
    op.drop_index("ix_carrito_items_producto_id", table_name="carrito_items")
    op.drop_index("ix_carrito_items_carrito_id", table_name="carrito_items")
    op.drop_table("carrito_items")
    op.drop_table("carritos")
    op.drop_index("ix_sesiones_ip_address", table_name="sesiones")
    op.drop_index("ix_sesiones_usuario_id", table_name="sesiones")
    op.drop_table("sesiones")
