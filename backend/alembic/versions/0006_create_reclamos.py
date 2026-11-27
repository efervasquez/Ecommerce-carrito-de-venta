"""crear reclamos, mermas y vinculo de reposicion

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reclamos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("pedido_origen_id", sa.BigInteger(), nullable=False),
        sa.Column("pedido_reposicion_id", sa.BigInteger(), nullable=True),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("foto_producto_url", sa.String(length=512), nullable=False),
        sa.Column("foto_comprobante_url", sa.String(length=512), nullable=False),
        sa.Column("foto_producto_path", sa.String(length=1024), nullable=False),
        sa.Column("foto_comprobante_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "estado", sa.String(length=32), nullable=False, server_default="aprobado"
        ),
        sa.Column(
            "intentos_adicionales_realizados",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("comprobante_verificado", sa.Boolean(), nullable=True),
        sa.Column("pertenencia_botica_verificada", sa.Boolean(), nullable=True),
        sa.Column("defecto_fisico_verificado", sa.Boolean(), nullable=True),
        sa.Column("motivo_falla", sa.String(length=255), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pedido_origen_id"], ["pedidos.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pedido_reposicion_id"], ["pedidos.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reclamos_pedido_origen_id", "reclamos", ["pedido_origen_id"]
    )
    op.create_index(
        "ix_reclamos_pedido_reposicion_id", "reclamos", ["pedido_reposicion_id"]
    )
    op.create_index("ix_reclamos_estado", "reclamos", ["estado"])
    op.create_index("ix_reclamos_creado_en", "reclamos", ["creado_en"])

    op.create_table(
        "merma_averiada",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("reclamo_id", sa.BigInteger(), nullable=False),
        sa.Column("pedido_id", sa.BigInteger(), nullable=True),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "cantidad", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reclamo_id"], ["reclamos.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pedido_id"], ["pedidos.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_merma_averiada_reclamo_id", "merma_averiada", ["reclamo_id"]
    )

    op.add_column("pedidos", sa.Column("reclamo_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_pedidos_reclamo_id", "pedidos", ["reclamo_id"])
    op.create_foreign_key(
        "fk_pedidos_reclamo",
        "pedidos",
        "reclamos",
        ["reclamo_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_pedidos_reclamo", "pedidos", type_="foreignkey")
    op.drop_index("ix_pedidos_reclamo_id", table_name="pedidos")
    op.drop_column("pedidos", "reclamo_id")

    # MySQL no permite soltar un indice que respalda una FK; drop_table elimina
    # la tabla junto con sus indices y constraints.
    op.drop_table("merma_averiada")
    op.drop_table("reclamos")
