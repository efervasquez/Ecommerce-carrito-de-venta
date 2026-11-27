import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ESTADOS_RECLAMO,
  getReclamo,
  getReclamos,
  Reclamo,
  ReclamoListado,
} from '../modules/reclamos/api';

export const BackofficeReclamos: React.FC = () => {
  const [estado, setEstado] = useState('');
  const [pedidoNumero, setPedidoNumero] = useState('');
  const [filtros, setFiltros] = useState<{ estado?: string; pedido_numero?: string }>({});
  const [detalleId, setDetalleId] = useState<number | null>(null);

  const reclamosQuery = useQuery({
    queryKey: ['backoffice-reclamos', filtros],
    queryFn: () => getReclamos(filtros),
  });
  const detalleQuery = useQuery({
    queryKey: ['backoffice-reclamo-detalle', detalleId],
    queryFn: () => getReclamo(detalleId as number),
    enabled: detalleId !== null,
  });

  const reclamos: ReclamoListado[] = Array.isArray(reclamosQuery.data)
    ? reclamosQuery.data
    : [];

  const aplicar = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFiltros({
      ...(estado ? { estado } : {}),
      ...(pedidoNumero ? { pedido_numero: pedidoNumero.trim() } : {}),
    });
  };

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Panel de reclamos</h1>
      </header>

      <form onSubmit={aplicar} style={styles.card}>
        <div style={styles.filters}>
          <label htmlFor="estado-filtro" style={styles.label}>
            Estado
          </label>
          <select
            id="estado-filtro"
            value={estado}
            onChange={(event) => setEstado(event.target.value)}
            style={styles.input}
          >
            <option value="">Todos</option>
            {ESTADOS_RECLAMO.map((valor) => (
              <option key={valor} value={valor}>
                {valor}
              </option>
            ))}
          </select>

          <label htmlFor="pedido-filtro" style={styles.label}>
            Pedido
          </label>
          <input
            id="pedido-filtro"
            type="text"
            value={pedidoNumero}
            onChange={(event) => setPedidoNumero(event.target.value)}
            placeholder="BL-..."
            style={styles.input}
          />

          <button type="submit" style={styles.primary}>
            Filtrar
          </button>
        </div>
      </form>

      {reclamosQuery.isLoading && <p role="status">Cargando reclamos...</p>}
      {reclamosQuery.isError && (
        <p role="alert" style={styles.error}>
          {(reclamosQuery.error as Error).message}
        </p>
      )}
      {!reclamosQuery.isLoading && !reclamosQuery.isError && reclamos.length === 0 && (
        <p>No hay reclamos para los filtros seleccionados.</p>
      )}

      <div style={styles.list}>
        {reclamos.map((reclamo) => {
          const escalado = reclamo.estado === 'escalado_supervision';
          const abierto = detalleId === reclamo.id;
          return (
            <article
              key={reclamo.id}
              style={escalado ? { ...styles.card, ...styles.escalado } : styles.card}
              aria-label={`Reclamo ${reclamo.id}`}
            >
              <div style={styles.row}>
                <strong style={styles.numero}>Reclamo #{reclamo.id}</strong>
                <span style={styles.badge}>{reclamo.estado}</span>
                {escalado && <span style={styles.alert}>Escalado a supervisión</span>}
              </div>
              <p style={styles.meta}>Pedido original: {reclamo.pedido_origen_numero}</p>
              <p style={styles.meta}>
                Pedido de reposición: {reclamo.pedido_reposicion_numero}
              </p>
              <p style={styles.meta}>Producto: {reclamo.producto_id}</p>
              <p style={styles.meta}>
                Intentos adicionales: {reclamo.intentos_adicionales_realizados}
              </p>
              <button
                type="button"
                onClick={() => setDetalleId(abierto ? null : reclamo.id)}
                style={styles.secondary}
              >
                {abierto ? 'Ocultar detalle' : 'Ver detalle'}
              </button>
              {abierto && (
                <DetalleReclamo
                  reclamo={detalleQuery.data}
                  cargando={detalleQuery.isLoading}
                  error={detalleQuery.isError ? (detalleQuery.error as Error).message : null}
                />
              )}
            </article>
          );
        })}
      </div>
    </main>
  );
};

function DetalleReclamo({
  reclamo,
  cargando,
  error,
}: {
  reclamo: Reclamo | undefined;
  cargando: boolean;
  error: string | null;
}) {
  if (cargando) return <p role="status">Cargando detalle...</p>;
  if (error) return <p role="alert" style={styles.error}>{error}</p>;
  if (!reclamo) return null;
  return (
    <div style={styles.detalle}>
      <p style={styles.meta}>Motivo: {reclamo.motivo}</p>
      {reclamo.descripcion && <p style={styles.meta}>Descripción: {reclamo.descripcion}</p>}
      <p style={styles.meta}>
        Reposición: {reclamo.pedido_reposicion_numero} ({reclamo.pedido_reposicion_estado})
      </p>
      <p style={styles.meta}>
        Intentos restantes: {reclamo.intentos_restantes}
      </p>
      <p style={styles.meta}>
        Comprobante verificado: {reclamo.comprobante_verificado ? 'sí' : 'no'} ·
        Pertenencia: {reclamo.pertenencia_botica_verificada ? 'sí' : 'no'} · Defecto
        físico: {reclamo.defecto_fisico_verificado ? 'sí' : 'no'}
      </p>
      {reclamo.motivo_falla && (
        <p style={styles.meta}>Motivo de falla: {reclamo.motivo_falla}</p>
      )}
      {reclamo.observaciones && (
        <p style={styles.meta}>Observaciones: {reclamo.observaciones}</p>
      )}
      <p style={styles.meta}>
        Evidencias: <a href={reclamo.foto_producto_url}>foto del producto</a> ·{' '}
        <a href={reclamo.foto_comprobante_url}>comprobante</a>
      </p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#f8fafc',
    padding: '1rem',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: { maxWidth: 1000, margin: '0 auto 1rem' },
  title: { color: '#1e293b' },
  card: {
    maxWidth: 1000,
    margin: '0.75rem auto',
    padding: '1rem',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
  },
  escalado: { borderColor: '#fca5a5', background: '#fff7f7' },
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
    marginTop: '0.5rem',
    padding: '0.4rem 0.7rem',
    border: '1px solid #cbd5e1',
    borderRadius: 4,
    background: '#f8fafc',
    color: '#334155',
  },
  list: { maxWidth: 1000, margin: '0 auto', display: 'grid', gap: '0.75rem' },
  row: { display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' },
  numero: { color: '#1e293b' },
  badge: {
    padding: '0.15rem 0.5rem',
    borderRadius: 999,
    background: '#e0f2fe',
    color: '#0369a1',
    fontSize: '0.85rem',
  },
  alert: {
    padding: '0.15rem 0.5rem',
    borderRadius: 999,
    background: '#fee2e2',
    color: '#b91c1c',
    fontSize: '0.85rem',
  },
  meta: { margin: '0.25rem 0', color: '#64748b', fontSize: '0.9rem' },
  error: { color: '#b91c1c' },
  detalle: {
    marginTop: '0.75rem',
    padding: '0.75rem',
    background: '#f8fafc',
    borderRadius: 6,
  },
};

export default BackofficeReclamos;
