import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  HistorialEstado,
  PedidoDespacho,
  asignarLote,
  getHistorial,
  getPedidos,
  getZonasDespacho,
} from '../services/despacho';

const ESTADOS = [
  'Registrado',
  'Preparando producto',
  'En camino',
  'Entregado',
  'incidencia_stock',
];

export const BackofficeDespacho: React.FC = () => {
  const queryClient = useQueryClient();
  const [estado, setEstado] = useState('');
  const [motorizadoId, setMotorizadoId] = useState('');
  const [seleccion, setSeleccion] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [historialNumero, setHistorialNumero] = useState<string | null>(null);

  const pedidosQuery = useQuery({
    queryKey: ['despacho-pedidos', estado],
    queryFn: () => getPedidos(estado ? { estado } : undefined),
  });
  const zonasQuery = useQuery({ queryKey: ['despacho-zonas'], queryFn: getZonasDespacho });
  const historialQuery = useQuery({
    queryKey: ['despacho-historial', historialNumero],
    queryFn: () => getHistorial(historialNumero as string),
    enabled: Boolean(historialNumero),
  });

  const pedidos = Array.isArray(pedidosQuery.data) ? pedidosQuery.data : [];
  const zonas = Array.isArray(zonasQuery.data) ? zonasQuery.data : [];

  const porZona = useMemo(() => {
    const grupos = new Map<number, PedidoDespacho[]>();
    for (const pedido of pedidos) {
      const lista = grupos.get(pedido.zona_id) ?? [];
      lista.push(pedido);
      grupos.set(pedido.zona_id, lista);
    }
    return Array.from(grupos.entries()).sort((a, b) => a[0] - b[0]);
  }, [pedidos]);

  const asignacion = useMutation({
    mutationFn: () => {
      const primero = pedidos.find((p) => p.numero === seleccion[0]);
      return asignarLote({
        zona_id: primero ? primero.zona_id : zonas[0]?.zona_id ?? 0,
        pedido_numeros: seleccion,
        motorizado_id: Number(motorizadoId),
      });
    },
    onSuccess: (data) => {
      setMessage(`Pedidos asignados: ${data.asignados.join(', ')}`);
      setSeleccion([]);
      queryClient.invalidateQueries({ queryKey: ['despacho-pedidos'] });
      queryClient.invalidateQueries({ queryKey: ['despacho-zonas'] });
    },
    onError: (error: Error) => setMessage(error.message),
  });

  const toggle = (numero: string) => {
    setSeleccion((actual) =>
      actual.includes(numero) ? actual.filter((n) => n !== numero) : [...actual, numero],
    );
  };

  const puedeAsignar =
    seleccion.length > 0 && Number.isInteger(Number(motorizadoId)) && Number(motorizadoId) > 0;

  if (pedidosQuery.isLoading) return <p role="status" style={styles.status}>Cargando despacho...</p>;
  if (pedidosQuery.isError) {
    return (
      <p role="alert" style={styles.error}>
        {(pedidosQuery.error as Error).message}
      </p>
    );
  }

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Buzón de despacho</h1>
      </header>

      <section aria-labelledby="zonas-title" style={styles.card}>
        <h2 id="zonas-title" style={styles.subtitle}>Resumen por zona</h2>
        {zonas.length === 0 ? (
          <p>No hay zonas registradas.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Zona</th>
                <th style={styles.th}>Distrito</th>
                <th style={styles.th}>Registrados</th>
                <th style={styles.th}>Preparando producto</th>
                <th style={styles.th}>En camino</th>
                <th style={styles.th}>Entregados</th>
              </tr>
            </thead>
            <tbody>
              {zonas.map((zona) => (
                <tr key={zona.zona_id}>
                  <td style={styles.td}>{zona.nombre}</td>
                  <td style={styles.td}>{zona.distrito}</td>
                  <td style={styles.td}>{zona.pedidos_registrados}</td>
                  <td style={styles.td}>{zona.pedidos_preparando}</td>
                  <td style={styles.td}>{zona.pedidos_en_camino}</td>
                  <td style={styles.td}>{zona.pedidos_entregados}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section style={styles.card}>
        <div style={styles.filters}>
          <label htmlFor="estado" style={styles.label}>
            Estado
          </label>
          <select
            id="estado"
            value={estado}
            onChange={(event) => setEstado(event.target.value)}
            style={styles.input}
          >
            <option value="">Todos</option>
            {ESTADOS.map((valor) => (
              <option key={valor} value={valor}>
                {valor}
              </option>
            ))}
          </select>

          <label htmlFor="motorizado" style={styles.label}>
            ID del motorizado
          </label>
          <input
            id="motorizado"
            type="number"
            min="1"
            value={motorizadoId}
            onChange={(event) => setMotorizadoId(event.target.value)}
            style={styles.input}
          />

          <button
            type="button"
            onClick={() => asignacion.mutate()}
            disabled={!puedeAsignar || asignacion.isPending}
            style={styles.primary}
          >
            Asignar lote
          </button>
        </div>
        {message && <p role="status" style={styles.message}>{message}</p>}
      </section>

      {porZona.length === 0 ? (
        <p>No hay pedidos para el filtro seleccionado.</p>
      ) : (
        porZona.map(([zonaId, lista]) => (
          <section key={zonaId} style={styles.card} aria-label={`Zona ${zonaId}`}>
            <h2 style={styles.subtitle}>
              Zona {zonaId} · {lista[0]?.distrito}
            </h2>
            {lista.map((pedido) => (
              <article key={pedido.numero} style={styles.row}>
                <input
                  type="checkbox"
                  aria-label={`Seleccionar ${pedido.numero}`}
                  checked={seleccion.includes(pedido.numero)}
                  onChange={() => toggle(pedido.numero)}
                />
                <span style={styles.numero}>{pedido.numero}</span>
                <span style={styles.badge}>{pedido.estado}</span>
                <span style={styles.meta}>
                  {pedido.metodo_entrega} · {pedido.monto.toFixed(2)} PEN
                </span>
                <span style={styles.meta}>
                  Motorizado: {pedido.motorizado_id ?? 'sin asignar'}
                </span>
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
            {historialNumero && lista.some((p) => p.numero === historialNumero) && (
              <Historial
                numero={historialNumero}
                items={historialQuery.data}
                loading={historialQuery.isLoading}
              />
            )}
          </section>
        ))
      )}
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
  header: { maxWidth: 1000, margin: '0 auto 1rem' },
  title: { color: '#1e293b' },
  subtitle: { fontSize: '1.15rem', color: '#1e293b' },
  card: { maxWidth: 1000, margin: '0.75rem auto', padding: '1rem', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 },
  filters: { display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' },
  label: { fontWeight: 600, color: '#334155' },
  input: { padding: '0.45rem', border: '1px solid #cbd5e1', borderRadius: 4 },
  primary: { padding: '0.55rem 0.9rem', border: 0, borderRadius: 5, background: '#0f766e', color: '#fff', fontWeight: 700 },
  secondary: { padding: '0.4rem 0.7rem', border: '1px solid #cbd5e1', borderRadius: 4, background: '#f8fafc', color: '#334155' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '0.45rem', borderBottom: '1px solid #e2e8f0', color: '#475569' },
  td: { padding: '0.45rem', borderBottom: '1px solid #f1f5f9' },
  row: { display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap', padding: '0.5rem 0', borderBottom: '1px solid #f1f5f9' },
  numero: { fontWeight: 700, color: '#1e293b' },
  badge: { padding: '0.15rem 0.5rem', borderRadius: 999, background: '#e0f2fe', color: '#0369a1', fontSize: '0.85rem' },
  meta: { color: '#64748b', fontSize: '0.9rem' },
  message: { marginTop: '0.75rem', padding: '0.6rem', background: '#ecfdf5', color: '#047857', borderRadius: 5 },
  historial: { marginTop: '0.75rem', padding: '0.75rem', background: '#f8fafc', borderRadius: 6 },
  historialTitle: { fontSize: '1rem', color: '#334155' },
  error: { padding: '1rem', color: '#b91c1c' },
  status: { padding: '2rem', color: '#475569' },
};

export default BackofficeDespacho;
