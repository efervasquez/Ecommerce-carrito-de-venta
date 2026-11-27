import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  HistorialEstado,
  autoAsignar,
  cambiarEstado,
  getHistorial,
  getMisPedidos,
  getPendientes,
} from '../services/despacho';
import { InspeccionCampo } from '../modules/reclamos/InspeccionCampo';

export const Despacho: React.FC = () => {
  const queryClient = useQueryClient();
  const [zonaId, setZonaId] = useState(1);
  const [message, setMessage] = useState<string | null>(null);
  const [historialNumero, setHistorialNumero] = useState<string | null>(null);

  const pendientesQuery = useQuery({
    queryKey: ['despacho-pendientes', zonaId],
    queryFn: () => getPendientes(zonaId),
    enabled: zonaId > 0,
  });
  const misPedidosQuery = useQuery({
    queryKey: ['despacho-mios'],
    queryFn: getMisPedidos,
  });
  const historialQuery = useQuery({
    queryKey: ['despacho-historial', historialNumero],
    queryFn: () => getHistorial(historialNumero as string),
    enabled: Boolean(historialNumero),
  });

  const pendientes = Array.isArray(pendientesQuery.data) ? pendientesQuery.data : [];
  const misPedidos = Array.isArray(misPedidosQuery.data) ? misPedidosQuery.data : [];

  const refrescar = () => {
    queryClient.invalidateQueries({ queryKey: ['despacho-pendientes'] });
    queryClient.invalidateQueries({ queryKey: ['despacho-mios'] });
  };

  const asignar = useMutation({
    mutationFn: (numero: string) => autoAsignar(numero),
    onSuccess: (pedido) => {
      setMessage(`Pedido ${pedido.numero} asignado.`);
      refrescar();
    },
    onError: (error: Error) => setMessage(error.message),
  });

  const avanzar = useMutation({
    mutationFn: ({ numero, estado }: { numero: string; estado: 'En camino' | 'Entregado' }) =>
      cambiarEstado(numero, estado),
    onSuccess: (pedido) => {
      setMessage(`Pedido ${pedido.numero} actualizado a ${pedido.estado}.`);
      refrescar();
    },
    onError: (error: Error) => setMessage(error.message),
  });

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Despacho de pedidos</h1>
        <div style={styles.filters}>
          <label htmlFor="zona" style={styles.label}>
            Zona
          </label>
          <input
            id="zona"
            type="number"
            min="1"
            value={zonaId}
            onChange={(event) => setZonaId(Number(event.target.value))}
            style={styles.input}
          />
        </div>
      </header>

      {message && <p role="status" style={styles.message}>{message}</p>}

      <section style={styles.card} aria-labelledby="pendientes-title">
        <h2 id="pendientes-title" style={styles.subtitle}>
          Pendientes (FIFO)
        </h2>
        {pendientesQuery.isLoading && <p role="status">Cargando pendientes...</p>}
        {pendientesQuery.isError && (
          <p role="alert" style={styles.error}>
            {(pendientesQuery.error as Error).message}
          </p>
        )}
        {!pendientesQuery.isLoading && pendientes.length === 0 && (
          <p>No hay pedidos pendientes en la zona.</p>
        )}
        {pendientes.map((pedido) => (
          <article key={pedido.numero} style={styles.row}>
            <span style={styles.numero}>{pedido.numero}</span>
            <span style={styles.badge}>{pedido.estado}</span>
            <span style={styles.meta}>
              {pedido.metodo_entrega} · {pedido.monto.toFixed(2)} PEN
            </span>
            <span style={styles.meta}>{new Date(pedido.creado_en).toLocaleString()}</span>
            <button
              type="button"
              onClick={() => asignar.mutate(pedido.numero)}
              disabled={asignar.isPending}
              style={styles.primary}
            >
              Auto-asignar
            </button>
          </article>
        ))}
      </section>

      <section style={styles.card} aria-labelledby="mios-title">
        <h2 id="mios-title" style={styles.subtitle}>Mis pedidos</h2>
        {misPedidos.length === 0 && <p>No tienes pedidos asignados.</p>}
        {misPedidos.map((pedido) => (
          <article key={pedido.numero} style={styles.row}>
            <span style={styles.numero}>{pedido.numero}</span>
            <span style={styles.badge}>{pedido.estado}</span>
            <span style={styles.meta}>
              {pedido.metodo_entrega} · {pedido.monto.toFixed(2)} PEN
            </span>
            {pedido.estado === 'Preparando producto' && (
              <button
                type="button"
                onClick={() => avanzar.mutate({ numero: pedido.numero, estado: 'En camino' })}
                disabled={avanzar.isPending}
                style={styles.primary}
              >
                En camino
              </button>
            )}
            {pedido.estado === 'En camino' && (
              <button
                type="button"
                onClick={() => avanzar.mutate({ numero: pedido.numero, estado: 'Entregado' })}
                disabled={avanzar.isPending}
                style={styles.primary}
              >
                Entregado
              </button>
            )}
            <button
              type="button"
              onClick={() =>
                setHistorialNumero(historialNumero === pedido.numero ? null : pedido.numero)
              }
              style={styles.secondary}
            >
              Ver historial
            </button>
          </article>
        ))}
        {historialNumero && misPedidos.some((p) => p.numero === historialNumero) && (
          <Historial
            numero={historialNumero}
            items={historialQuery.data}
            loading={historialQuery.isLoading}
          />
        )}
      </section>

      <InspeccionCampo />
    </main>
  );
};

function Historial({
  numero,
  items,
  loading,
}: {
  numero: string;
  items: HistorialEstado[] | undefined;
  loading: boolean;
}) {
  if (loading) return <p role="status">Cargando historial...</p>;
  const filas = Array.isArray(items) ? items : [];
  return (
    <div style={styles.historial} aria-label={`Historial de ${numero}`}>
      <h3 style={styles.historialTitle}>Historial de {numero}</h3>
      {filas.length === 0 ? (
        <p>Sin transiciones registradas.</p>
      ) : (
        <ol>
          {filas.map((fila, index) => (
            <li key={`${fila.estado_nuevo}-${index}`}>
              {fila.estado_anterior ?? '—'} → {fila.estado_nuevo} · {new Date(fila.timestamp).toLocaleString()}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#f8fafc', padding: '1rem', fontFamily: 'system-ui, -apple-system, sans-serif' },
  header: { maxWidth: 900, margin: '0 auto 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' },
  title: { color: '#1e293b' },
  subtitle: { fontSize: '1.15rem', color: '#1e293b' },
  filters: { display: 'flex', gap: '0.5rem', alignItems: 'center' },
  label: { fontWeight: 600, color: '#334155' },
  input: { width: 90, padding: '0.45rem', border: '1px solid #cbd5e1', borderRadius: 4 },
  card: { maxWidth: 900, margin: '0.75rem auto', padding: '1rem', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 },
  row: { display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap', padding: '0.5rem 0', borderBottom: '1px solid #f1f5f9' },
  numero: { fontWeight: 700, color: '#1e293b' },
  badge: { padding: '0.15rem 0.5rem', borderRadius: 999, background: '#e0f2fe', color: '#0369a1', fontSize: '0.85rem' },
  meta: { color: '#64748b', fontSize: '0.9rem' },
  primary: { padding: '0.5rem 0.85rem', border: 0, borderRadius: 5, background: '#0f766e', color: '#fff', fontWeight: 700 },
  secondary: { padding: '0.4rem 0.7rem', border: '1px solid #cbd5e1', borderRadius: 4, background: '#f8fafc', color: '#334155' },
  message: { maxWidth: 900, margin: '0 auto 0.5rem', padding: '0.6rem', background: '#ecfdf5', color: '#047857', borderRadius: 5 },
  historial: { marginTop: '0.75rem', padding: '0.75rem', background: '#f8fafc', borderRadius: 6 },
  historialTitle: { fontSize: '1rem', color: '#334155' },
  error: { color: '#b91c1c' },
};

export default Despacho;
