export interface ProductoCatalogo {
  id: number;
  nombre: string;
  componentes: string;
  imagen_url: string | null;
  precio_regular: number;
  moneda: string;
  descuento_porcentaje: number;
  stock_disponible: number;
  stock_bajo: boolean;
  precios_bajos: boolean;
  requiere_receta: boolean;
}

export interface CatalogoResponse {
  items: ProductoCatalogo[];
  next_cursor: string | null;
  has_next: boolean;
}

export interface ProductoDetalle extends ProductoCatalogo {
  detalle: string;
  presentacion: string;
  metodos_entrega: string[];
  contraindicaciones: string;
  precauciones_advertencias: string;
  reacciones_adversas: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export async function buscarCatalogo(
  q: string,
  cursor: string | null,
  limit = 8,
): Promise<CatalogoResponse> {
  const params = new URLSearchParams({ q, limit: String(limit) });
  if (cursor) params.set('cursor', cursor);
  const response = await fetch(`${API_BASE_URL}/catalogo/buscar?${params.toString()}`);
  const body = (await response.json()) as CatalogoResponse | { detail?: string };
  if (!response.ok) {
    throw new Error('detail' in body && body.detail ? body.detail : 'No se pudo cargar el catálogo.');
  }
  return body as CatalogoResponse;
}

export async function obtenerProductoDetalle(productoId: string): Promise<ProductoDetalle> {
  const response = await fetch(`${API_BASE_URL}/catalogo/productos/${encodeURIComponent(productoId)}`);
  const body = (await response.json()) as ProductoDetalle | { detail?: string };
  if (!response.ok) {
    throw new Error('detail' in body && body.detail ? body.detail : 'No se pudo cargar el producto.');
  }
  return body as ProductoDetalle;
}
