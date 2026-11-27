"""crear recetas/OCRJob y asociacion de receta al carrito y pedido

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recetas",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=32), nullable=False, server_default="procesando"),
        sa.Column("nombre_archivo", sa.String(length=255), nullable=True),
        sa.Column("receta_id", sa.String(length=64), nullable=True),
        sa.Column("items_json", sa.Text(), nullable=True),
        sa.Column("sugeridos_json", sa.Text(), nullable=True),
        sa.Column("faltantes_json", sa.Text(), nullable=True),
        sa.Column("confianza", sa.Float(), nullable=True),
        sa.Column("mensaje", sa.String(length=500), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receta_id"),
    )
    op.create_index("ix_recetas_usuario_id", "recetas", ["usuario_id"])
    op.create_index("ix_recetas_receta_id", "recetas", ["receta_id"])

    op.add_column("carritos", sa.Column("receta_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_carritos_receta", "carritos", "recetas", ["receta_id"], ["id"], ondelete="SET NULL"
    )

    op.add_column("pedidos", sa.Column("receta_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "pedidos",
        sa.Column(
            "auditoria_receta_pendiente",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_foreign_key(
        "fk_pedidos_receta", "pedidos", "recetas", ["receta_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_pedidos_receta", "pedidos", type_="foreignkey")
    op.drop_column("pedidos", "auditoria_receta_pendiente")
    op.drop_column("pedidos", "receta_id")
    op.drop_constraint("fk_carritos_receta", "carritos", type_="foreignkey")
    op.drop_column("carritos", "receta_id")
    op.drop_index("ix_recetas_receta_id", table_name="recetas")
    op.drop_index("ix_recetas_usuario_id", table_name="recetas")
    op.execute("DROP TABLE IF EXISTS recetas")
