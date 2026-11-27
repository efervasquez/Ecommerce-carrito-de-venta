import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

export interface VentasReporte {
  fecha_inicio: string;
  fecha_fin: string;
  total_ordenes: number;
  unidades_vendidas: number;
  monto_total_facturado: number;
  moneda: string;
}

export interface PedidoBalance {
  balance: Record<string, number>;
  total_pedidos: number;
}

export interface ProductoStockCritico {
  producto_id: number;
  nombre: string;
  stock_disponible: number;
}

export interface ProductoRotacion {
  producto_id: number;
  nombre: string;
  unidades_vendidas: number;
}

export interface InventarioCritico {
  stock_bajo: ProductoStockCritico[];
  quiebres: ProductoStockCritico[];
  mayor_rotacion: ProductoRotacion[];
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';
const ESTADOS = ['Registrado', 'Preparando producto', 'En camino', 'Entregado'];

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: authHeaders(),
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

export function getVentas(
  fechaInicio: string,
  fechaFin: string,
): Promise<VentasReporte> {
  const search = new URLSearchParams({
    fecha_inicio: fechaInicio,
    fecha_fin: fechaFin,
  });
  return request<VentasReporte>(`/backoffice/reportes/ventas?${search.toString()}`);
}

export function getPedidosBalance(): Promise<PedidoBalance> {
  return request<PedidoBalance>('/backoffice/reportes/pedidos-balance');
}

export function getInventarioCritico(): Promise<InventarioCritico> {
  return request<InventarioCritico>('/backoffice/reportes/inventario-critico');
}

function fechaIso(fecha: Date): string {
  const anio = fecha.getFullYear();
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');
  return `${anio}-${mes}-${dia}`;
}

export const BackofficeReportes: React.FC = () => {
  const hoy = new Date();
  const inicioMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
  const [fechaInicio, setFechaInicio] = useState(fechaIso(inicioMes));
  const [fechaFin, setFechaFin] = useState(fechaIso(hoy));
  const [rango, setRango] = useState({
    inicio: fechaIso(inicioMes),
    fin: fechaIso(hoy),
  });

  const ventasQuery = useQuery({
    queryKey: ['reportes-ventas', rango],
    queryFn: () => getVentas(rango.inicio, rango.fin),
  });
  const balanceQuery = useQuery({
    queryKey: ['reportes-balance'],
    queryFn: getPedidosBalance,
  });
  const inventarioQuery = useQuery({
    queryKey: ['reportes-inventario'],
    queryFn: getInventarioCritico,
  });

  const consultar = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setRango({ inicio: fechaInicio, fin: fechaFin });
  };

  const ventas = ventasQuery.data;
  const balance = balanceQuery.data;
  const inventario = inventarioQuery.data;

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Reportes del Backoffice</h1>
      </header>

      <section style={styles.card}>
        <h2 style={styles.subtitle}>Ventas y facturación</h2>
        <form onSubmit={consultar} style={styles.filters}>
          <label htmlFor="fecha_inicio" style={styles.label}>
            Fecha de inicio
          </label>
          <input
            id="fecha_inicio"
            name="fecha_inicio"
            type="date"
            value={fechaInicio}
            onChange={(event) => setFechaInicio(event.target.value)}
            style={styles.input}
          />

          <label htmlFor="fecha_fin" style={styles.label}>
            Fecha de fin
          </label>
          <input
            id="fecha_fin"
            name="fecha_fin"
            type="date"
            value={fechaFin}
            onChange={(event) => setFechaFin(event.target.value)}
            style={styles.input}
          />

          <button type="submit" style={styles.primary}>
            Consultar
          </button>
        </form>

        {ventasQuery.isLoading && <p role="status">Cargando ventas...</p>}
        {ventasQuery.isError && (
          <p role="alert" style={styles.error}>
            {(ventasQuery.error as Error).message}
          </p>
        )}
        {ventas && (
          <div style={styles.metrics}>
            <article style={styles.metric}>
              <span style={styles.metricLabel}>Total de órdenes</span>
              <strong style={styles.metricValue}>{ventas.total_ordenes}</strong>
            </article>
            <article style={styles.metric}>
              <span style={styles.metricLabel}>Unidades vendidas</span>
              <strong style={styles.metricValue}>{ventas.unidades_vendidas}</strong>
            </article>
            <article style={styles.metric}>
              <span style={styles.metricLabel}>Monto total facturado</span>
              <strong style={styles.metricValue}>
                {ventas.monto_total_facturado.toFixed(2)} {ventas.moneda}
              </strong>
            </article>
          </div>
        )}
        {ventas && (
          <p style={styles.rango}>
            Periodo: {ventas.fecha_inicio} al {ventas.fecha_fin}
          </p>
        )}
      </section>

      <section style={styles.card}>
        <h2 style={styles.subtitle}>Balance de pedidos</h2>
        {balanceQuery.isLoading && <p role="status">Cargando balance...</p>}
        {balanceQuery.isError && (
          <p role="alert" style={styles.error}>
            {(balanceQuery.error as Error).message}
          </p>
        )}
        {balance && (
          <>
            <div style={styles.metrics}>
              {ESTADOS.map((estado) => (
                <article key={estado} style={styles.metric}>
                  <span style={styles.metricLabel}>{estado}</span>
                  <strong style={styles.metricValue}>
                    {balance.balance[estado] ?? 0}
                  </strong>
                </article>
              ))}
              <article style={styles.metric}>
                <span style={styles.metricLabel}>Total de pedidos</span>
                <strong style={styles.metricValue}>{balance.total_pedidos}</strong>
              </article>
            </div>
          </>
        )}
      </section>

      <section style={styles.card}>
        <h2 style={styles.subtitle}>Inventario crítico</h2>
        {inventarioQuery.isLoading && <p role="status">Cargando inventario...</p>}
        {inventarioQuery.isError && (
          <p role="alert" style={styles.error}>
            {(inventarioQuery.error as Error).message}
          </p>
        )}
        {inventario && (
          <div style={styles.inventario}>
            <div>
              <h3 style={styles.subtitleSmall}>Stock bajo (&lt; 6 unidades)</h3>
              <TablaStock items={inventario.stock_bajo} />
            </div>
            <div>
              <h3 style={styles.subtitleSmall}>Quiebres de stock</h3>
              <TablaStock items={inventario.quiebres} />
            </div>
            <div>
              <h3 style={styles.subtitleSmall}>Mayor rotación</h3>
              <TablaRotacion items={inventario.mayor_rotacion} />
            </div>
          </div>
        )}
      </section>
    </main>
  );
};

function TablaStock({ items }: { items: ProductoStockCritico[] }) {
  if (items.length === 0) {
    return <p style={styles.empty}>Sin productos.</p>;
  }
  return (
    <table style={styles.table}>
      <thead>
        <tr>
          <th style={styles.th}>Producto</th>
          <th style={styles.th}>Stock disponible</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.producto_id}>
            <td style={styles.td}>{item.nombre}</td>
            <td style={styles.td}>{item.stock_disponible}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TablaRotacion({ items }: { items: ProductoRotacion[] }) {
  if (items.length === 0) {
    return <p style={styles.empty}>Sin ventas registradas.</p>;
  }
  return (
    <table style={styles.table}>
      <thead>
        <tr>
          <th style={styles.th}>Producto</th>
          <th style={styles.th}>Unidades vendidas</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.producto_id}>
            <td style={styles.td}>{item.nombre}</td>
            <td style={styles.td}>{item.unidades_vendidas}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#f8fafc',
    padding: '1rem',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: { maxWidth: 1100, margin: '0 auto 1rem' },
  title: { color: '#1e293b' },
  subtitle: { fontSize: '1.15rem', color: '#1e293b' },
  subtitleSmall: { fontSize: '1rem', color: '#334155' },
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
  metrics: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
    gap: '0.75rem',
    marginTop: '0.75rem',
  },
  metric: {
    padding: '0.75rem',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 6,
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  },
  metricLabel: { color: '#64748b', fontSize: '0.85rem' },
  metricValue: { color: '#0f172a', fontSize: '1.4rem' },
  rango: { color: '#94a3b8', fontSize: '0.85rem' },
  inventario: { display: 'grid', gap: '1rem' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: {
    textAlign: 'left',
    padding: '0.45rem',
    borderBottom: '1px solid #e2e8f0',
    color: '#475569',
  },
  td: { padding: '0.45rem', borderBottom: '1px solid #f1f5f9' },
  empty: { color: '#94a3b8', fontSize: '0.9rem' },
  error: { color: '#b91c1c' },
};

export default BackofficeReportes;
