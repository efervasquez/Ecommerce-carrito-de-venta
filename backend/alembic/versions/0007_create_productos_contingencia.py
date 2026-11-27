"""crear productos locales y auditoria de ajustes de inventario

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-26
"""
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "productos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("componentes", sa.String(length=255), nullable=False),
        sa.Column("precio_regular", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "moneda", sa.String(length=8), nullable=False, server_default="PEN"
        ),
        sa.Column(
            "descuento_porcentaje",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "precios_bajos", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column(
            "requiere_receta", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column("presentacion", sa.String(length=255), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=False),
        sa.Column("imagen_url", sa.String(length=512), nullable=True),
        sa.Column("metodos_entrega", sa.JSON(), nullable=False),
        sa.Column("contraindicaciones", sa.Text(), nullable=True),
        sa.Column("precauciones_advertencias", sa.Text(), nullable=True),
        sa.Column("reacciones_adversas", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_productos_nombre", "productos", ["nombre"])

    op.create_table(
        "inventario_ajustes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("stock_anterior", sa.Integer(), nullable=False),
        sa.Column("stock_nuevo", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["producto_id"], ["productos.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventario_ajustes_producto_id", "inventario_ajustes", ["producto_id"]
    )
    op.create_index(
        "ix_inventario_ajustes_creado_en", "inventario_ajustes", ["creado_en"]
    )

    _sembrar_catalogo_inicial()


def _sembrar_catalogo_inicial() -> None:
    """Importa el catalogo vigente para que el backoffice opere sobre el."""
    seed_path = Path(__file__).resolve().parents[3] / "infra" / "catalogo-seed.json"
    if not seed_path.is_file():
        return
    productos = json.loads(seed_path.read_text(encoding="utf-8"))
    conn = op.get_bind()
    for producto in productos:
        metodos = []
        for metodo in producto.get("metodos_entrega") or []:
            normalizado = str(metodo).strip().lower()
            if "delivery" in normalizado:
                metodos.append("delivery")
            elif "retiro" in normalizado:
                metodos.append("retiro")
        if not metodos:
            metodos = ["delivery", "retiro"]
        conn.execute(
            sa.text(
                "INSERT INTO productos (id, nombre, componentes, precio_regular, "
                "moneda, descuento_porcentaje, precios_bajos, requiere_receta, "
                "presentacion, detalle, imagen_url, metodos_entrega, "
                "contraindicaciones, precauciones_advertencias, "
                "reacciones_adversas, creado_en, actualizado_en) "
                "VALUES (:id, :nombre, :componentes, :precio_regular, :moneda, "
                ":descuento_porcentaje, :precios_bajos, :requiere_receta, "
                ":presentacion, :detalle, :imagen_url, :metodos_entrega, "
                ":contraindicaciones, :precauciones_advertencias, "
                ":reacciones_adversas, NOW(), NOW())"
            ),
            {
                "id": int(producto["id"]),
                "nombre": producto["nombre"],
                "componentes": producto.get("componentes", ""),
                "precio_regular": float(producto.get("precio_regular", 0)),
                "moneda": producto.get("moneda", "PEN"),
                "descuento_porcentaje": float(
                    producto.get("descuento_porcentaje", 0)
                ),
                "precios_bajos": bool(producto.get("precios_bajos", False)),
                "requiere_receta": bool(producto.get("requiere_receta", False)),
                "presentacion": producto.get("presentacion", ""),
                "detalle": producto.get("detalle", ""),
                "imagen_url": producto.get("imagen_url"),
                "metodos_entrega": json.dumps(metodos, ensure_ascii=False),
                "contraindicaciones": producto.get("contraindicaciones", ""),
                "precauciones_advertencias": producto.get(
                    "precauciones_advertencias", ""
                ),
                "reacciones_adversas": producto.get("reacciones_adversas", ""),
            },
        )
        conn.execute(
            sa.text(
                "INSERT IGNORE INTO inventario_stock "
                "(producto_id, disponible, reservado, actualizado_en) "
                "VALUES (:id, :disponible, 0, NOW())"
            ),
            {
                "id": int(producto["id"]),
                "disponible": int(producto.get("stock_disponible", 0)),
            },
        )


def downgrade() -> None:
    op.drop_table("inventario_ajustes")
    op.drop_table("productos")
