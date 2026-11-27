"""crear zonas, direcciones, pedidos, items de pedido y pagos

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zonas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("distrito", sa.String(length=120), nullable=False),
        sa.Column("tiempo_estimado_min", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "direcciones",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("zona_id", sa.BigInteger(), nullable=False),
        sa.Column("direccion_linea1", sa.String(length=255), nullable=False),
        sa.Column("referencia", sa.String(length=255), nullable=True),
        sa.Column("telefono_contacto", sa.String(length=32), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zona_id"], ["zonas.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_direcciones_usuario_id", "direcciones", ["usuario_id"])
    op.create_index("ix_direcciones_zona_id", "direcciones", ["zona_id"])

    op.create_table(
        "pedidos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("numero", sa.String(length=32), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("carrito_id", sa.BigInteger(), nullable=False),
        sa.Column("direccion_id", sa.BigInteger(), nullable=True),
        sa.Column("zona_id", sa.BigInteger(), nullable=False),
        sa.Column("metodo_entrega", sa.String(length=16), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False, server_default="venta"),
        sa.Column("estado", sa.String(length=32), nullable=False, server_default="Registrado"),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("moneda", sa.String(length=8), nullable=False, server_default="PEN"),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrito_id"], ["carritos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["direccion_id"], ["direcciones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["zona_id"], ["zonas.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero"),
    )
    op.create_index("ix_pedidos_numero", "pedidos", ["numero"])
    op.create_index("ix_pedidos_usuario_id", "pedidos", ["usuario_id"])
    op.create_index("ix_pedidos_carrito_id", "pedidos", ["carrito_id"])
    op.create_index("ix_pedidos_zona_id", "pedidos", ["zona_id"])

    op.create_table(
        "pedido_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.BigInteger(), nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pedido_items_pedido_id", "pedido_items", ["pedido_id"])

    op.create_table(
        "pagos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("payment_intent_id", sa.String(length=255), nullable=False),
        sa.Column("idempotencia_key", sa.String(length=255), nullable=False),
        sa.Column("carrito_id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("intento", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("direccion_id", sa.BigInteger(), nullable=True),
        sa.Column("zona_id", sa.BigInteger(), nullable=False),
        sa.Column("metodo_entrega", sa.String(length=16), nullable=False, server_default="retiro"),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("moneda", sa.String(length=8), nullable=False, server_default="PEN"),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="procesando"),
        sa.Column("pedido_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["carrito_id"], ["carritos.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["direccion_id"], ["direcciones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["zona_id"], ["zonas.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_intent_id"),
        sa.UniqueConstraint("idempotencia_key", name="uq_pago_idempotencia"),
    )
    op.create_index("ix_pagos_payment_intent_id", "pagos", ["payment_intent_id"])
    op.create_index("ix_pagos_carrito_id", "pagos", ["carrito_id"])
    op.create_index("ix_pagos_usuario_id", "pagos", ["usuario_id"])

    # Seed minimo de zonas activas para la demo (ADR-0003).
    op.execute(
        "INSERT INTO zonas (nombre, distrito, tiempo_estimado_min, activo, creado_en) "
        "VALUES ('Botica Centro', 'Centro', 30, 1, CURRENT_TIMESTAMP)"
    )


def downgrade() -> None:
    # En MySQL los indices se eliminan con la tabla y no pueden borrarse antes
    # si participan en una foreign key: se droppan las tablas en orden inverso.
    for table in ("pagos", "pedido_items", "pedidos", "direcciones", "zonas"):
        op.execute(f"DROP TABLE IF EXISTS {table}")
