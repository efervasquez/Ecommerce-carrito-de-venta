import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { ESTADOS_RECLAMO, getReclamos, ReclamoListado } from '../modules/reclamos/api';

export const Reclamos: React.FC = () => {
  const reclamosQuery = useQuery({
    queryKey: ['reclamos'],
    queryFn: () => getReclamos(),
  });

  const reclamos: ReclamoListado[] = Array.isArray(reclamosQuery.data)
    ? reclamosQuery.data
    : [];

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Historial de reclamos</h1>
        <Link to="/reclamos/nuevo" style={styles.link}>
          Registrar un reclamo
        </Link>
      </header>

      {reclamosQuery.isLoading && <p role="status">Cargando reclamos...</p>}
      {reclamosQuery.isError && (
        <p role="alert" style={styles.error}>
          {(reclamosQuery.error as Error).message}
        </p>
      )}

      {!reclamosQuery.isLoading && !reclamosQuery.isError && reclamos.length === 0 && (
        <p>No tienes reclamos registrados.</p>
      )}

      <div style={styles.list}>
        {reclamos.map((reclamo) => (
          <article key={reclamo.id} style={styles.card} aria-label={`Reclamo ${reclamo.id}`}>
            <div style={styles.row}>
              <strong style={styles.numero}>Reclamo #{reclamo.id}</strong>
              <span style={styles.badge}>{reclamo.estado}</span>
            </div>
            <p style={styles.meta}>Pedido original: {reclamo.pedido_origen_numero}</p>
            <p style={styles.meta}>
              Pedido de reposición: {reclamo.pedido_reposicion_numero}
            </p>
            <p style={styles.meta}>Producto: {reclamo.producto_id}</p>
            <p style={styles.meta}>
              Intentos adicionales: {reclamo.intentos_adicionales_realizados}
            </p>
            <p style={styles.meta}>
              Registrado: {new Date(reclamo.creado_en).toLocaleString()}
            </p>
          </article>
        ))}
      </div>

      <p style={styles.estados}>
        Estados posibles: {ESTADOS_RECLAMO.join(' · ')}
      </p>
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
    maxWidth: 900,
    margin: '0 auto 1rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  title: { color: '#1e293b' },
  link: { color: '#2563eb' },
  list: { maxWidth: 900, margin: '0 auto', display: 'grid', gap: '0.75rem' },
  card: {
    padding: '1rem',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
  },
  row: { display: 'flex', gap: '0.6rem', alignItems: 'center' },
  numero: { color: '#1e293b' },
  badge: {
    padding: '0.15rem 0.5rem',
    borderRadius: 999,
    background: '#e0f2fe',
    color: '#0369a1',
    fontSize: '0.85rem',
  },
  meta: { margin: '0.25rem 0', color: '#64748b', fontSize: '0.9rem' },
  error: { color: '#b91c1c' },
  estados: {
    maxWidth: 900,
    margin: '1rem auto',
    color: '#94a3b8',
    fontSize: '0.85rem',
  },
};

export default Reclamos;
