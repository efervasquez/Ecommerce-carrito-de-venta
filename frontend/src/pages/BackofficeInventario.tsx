import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

export interface ProductoListado {
  id: number;
  nombre: string;
  componentes: string;
  precio_regular: number;
  descuento_porcentaje: number;
  stock_disponible: number;
  stock_reservado: number;
  precios_bajos: boolean;
  requiere_receta: boolean;
}

export interface ProductoListadoResponse {
  items: ProductoListado[];
  total: number;
}

export interface ProductoDetalle extends ProductoListado {
  moneda: string;
  presentacion: string;
  detalle: string;
  imagen_url: string | null;
  metodos_entrega: string[];
  contraindicaciones: string | null;
  precauciones_advertencias: string | null;
  reacciones_adversas: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface ProductoPayload {
  nombre: string;
  componentes: string;
  precio_regular: number;
  moneda: string;
  descuento_porcentaje: number;
  precios_bajos: boolean;
  requiere_receta: boolean;
  presentacion: string;
  detalle: string;
  imagen_url?: string | null;
  metodos_entrega: string[];
  contraindicaciones?: string;
  precauciones_advertencias?: string;
  reacciones_adversas?: string;
  stock_disponible?: number;
}

export interface StockAjusteResponse {
  id: number;
  producto_id: number;
  disponible: number;
  reservado: number;
  actualizado_en: string;
}

export const METODOS_ENTREGA = ['delivery', 'retiro'] as const;

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
  });
  const texto = await response.text();
  let body: unknown = null;
  if (texto) {
    try {
      body = JSON.parse(texto);
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    const detalle =
      body && typeof body === 'object' && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : 'No se pudo completar la solicitud.';
    throw new Error(detalle);
  }
  return body as T;
}

export function getProductos(params?: {
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<ProductoListadoResponse> {
  const search = new URLSearchParams();
  if (params?.q) search.set('q', params.q);
  if (params?.limit !== undefined) search.set('limit', String(params.limit));
  if (params?.offset !== undefined) search.set('offset', String(params.offset));
  const query = search.toString();
  return request<ProductoListadoResponse>(
    `/backoffice/productos${query ? `?${query}` : ''}`,
  );
}

export function getProducto(id: number): Promise<ProductoDetalle> {
  return request<ProductoDetalle>(`/backoffice/productos/${id}`);
}

export function crearProducto(payload: ProductoPayload): Promise<ProductoDetalle> {
  return request<ProductoDetalle>('/backoffice/productos', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function actualizarProducto(
  id: number,
  payload: ProductoPayload,
): Promise<ProductoDetalle> {
  return request<ProductoDetalle>(`/backoffice/productos/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function ajustarStock(
  id: number,
  stockDisponible: number,
  motivo?: string,
): Promise<StockAjusteResponse> {
  return request<StockAjusteResponse>(`/backoffice/productos/${id}/stock`, {
    method: 'PATCH',
    body: JSON.stringify({
      stock_disponible: stockDisponible,
      ...(motivo ? { motivo } : {}),
    }),
  });
}

export const BackofficeInventario: React.FC = () => {
  const queryClient = useQueryClient();
  const [q, setQ] = useState('');
  const [qAplicado, setQAplicado] = useState('');
  const [ediciones, setEdiciones] = useState<Record<number, string>>({});
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const listaQuery = useQuery({
    queryKey: ['inventario-productos', qAplicado],
    queryFn: () => getProductos({ q: qAplicado || undefined, limit: 100 }),
  });

  const stockMutation = useMutation({
    mutationFn: ({ id, value }: { id: number; value: string }) =>
      ajustarStock(id, Number(value), 'Ajuste manual de contingencia'),
    onSuccess: (data) => {
      setMensaje(
        `Stock actualizado: disponible ${data.disponible}, reservado ${data.reservado}.`,
      );
      setError(null);
      setEdiciones((actual) => {
        const copia = { ...actual };
        delete copia[data.producto_id];
        return copia;
      });
      queryClient.invalidateQueries({ queryKey: ['inventario-productos'] });
    },
    onError: (err: Error) => {
      setError(err.message);
      setMensaje(null);
    },
  });

  const items: ProductoListado[] = listaQuery.data?.items ?? [];

  const aplicarBusqueda = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setQAplicado(q.trim());
  };

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Inventario</h1>
        <Link to="/backoffice/inventario/nuevo" style={styles.link}>
          Registrar nuevo producto
        </Link>
      </header>

      <form onSubmit={aplicarBusqueda} style={styles.card}>
        <div style={styles.filters}>
          <label htmlFor="buscar-inventario" style={styles.label}>
            Buscar por nombre o componente
          </label>
          <input
            id="buscar-inventario"
            name="q"
            type="text"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Nombre o componente"
            style={styles.input}
          />
          <button type="submit" style={styles.primary}>
            Buscar
          </button>
        </div>
      </form>

      {mensaje && (
        <p role="status" style={styles.message}>
          {mensaje}
        </p>
      )}
      {error && (
        <p role="alert" style={styles.error}>
          {error}
        </p>
      )}

      {listaQuery.isLoading && <p role="status">Cargando inventario...</p>}
      {listaQuery.isError && (
        <p role="alert" style={styles.error}>
          {(listaQuery.error as Error).message}
        </p>
      )}
      {!listaQuery.isLoading && !listaQuery.isError && items.length === 0 && (
        <p>No hay productos para el filtro seleccionado.</p>
      )}

      {items.length > 0 && (
        <section style={styles.card}>
          <p style={styles.total}>Total de productos: {listaQuery.data?.total ?? items.length}</p>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Producto</th>
                <th style={styles.th}>Componentes</th>
                <th style={styles.th}>Precio</th>
                <th style={styles.th}>Descuento</th>
                <th style={styles.th}>Disponible</th>
                <th style={styles.th}>Reservado</th>
                <th style={styles.th}>Precios bajos</th>
                <th style={styles.th}>Receta</th>
                <th style={styles.th}>Ajuste de stock</th>
                <th style={styles.th}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const valor =
                  ediciones[item.id] ?? String(item.stock_disponible);
                return (
                  <tr key={item.id}>
                    <td style={styles.td}>{item.nombre}</td>
                    <td style={styles.td}>{item.componentes}</td>
                    <td style={styles.td}>{item.precio_regular.toFixed(2)} PEN</td>
                    <td style={styles.td}>{item.descuento_porcentaje.toFixed(2)}%</td>
                    <td style={styles.td}>{item.stock_disponible}</td>
                    <td style={styles.td}>{item.stock_reservado}</td>
                    <td style={styles.td}>{item.precios_bajos ? 'Sí' : 'No'}</td>
                    <td style={styles.td}>{item.requiere_receta ? 'Sí' : 'No'}</td>
                    <td style={styles.td}>
                      <input
                        type="number"
                        min="0"
                        step="1"
                        aria-label={`Stock disponible de ${item.nombre}`}
                        name={`stock-${item.id}`}
                        value={valor}
                        onChange={(event) =>
                          setEdiciones((actual) => ({
                            ...actual,
                            [item.id]: event.target.value,
                          }))
                        }
                        style={styles.stockInput}
                      />
                      <button
                        type="button"
                        aria-label={`Guardar stock de ${item.nombre}`}
                        onClick={() =>
                          stockMutation.mutate({ id: item.id, value: valor })
                        }
                        disabled={stockMutation.isPending}
                        style={styles.secondary}
                      >
                        Guardar
                      </button>
                    </td>
                    <td style={styles.td}>
                      <Link
                        to={`/backoffice/inventario/${item.id}/editar`}
                        style={styles.link}
                      >
                        Editar
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#f8fafc',
    padding: '1rem',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    maxWidth: 1100,
    margin: '0 auto 1rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  title: { color: '#1e293b' },
  link: { color: '#2563eb' },
  card: {
    maxWidth: 1100,
    margin: '0.75rem auto',
    padding: '1rem',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
  },
  filters: { display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' },
  label: { fontWeight: 600, color: '#334155' },
  input: { padding: '0.45rem', border: '1px solid #cbd5e1', borderRadius: 4 },
  primary: {
    padding: '0.55rem 0.9rem',
    border: 0,
    borderRadius: 5,
    background: '#0f766e',
    color: '#fff',
    fontWeight: 700,
  },
  secondary: {
    marginLeft: '0.4rem',
    padding: '0.4rem 0.7rem',
    border: '1px solid #cbd5e1',
    borderRadius: 4,
    background: '#f8fafc',
    color: '#334155',
  },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    textAlign: 'left',
    padding: '0.45rem',
    borderBottom: '1px solid #e2e8f0',
    color: '#475569',
  },
  td: { padding: '0.45rem', borderBottom: '1px solid #f1f5f9' },
  stockInput: {
    width: 80,
    padding: '0.35rem',
    border: '1px solid #cbd5e1',
    borderRadius: 4,
  },
  total: { color: '#64748b', fontSize: '0.9rem' },
  message: {
    maxWidth: 1100,
    margin: '0 auto 0.5rem',
    padding: '0.6rem',
    background: '#ecfdf5',
    color: '#047857',
    borderRadius: 5,
  },
  error: { color: '#b91c1c' },
};

export default BackofficeInventario;
