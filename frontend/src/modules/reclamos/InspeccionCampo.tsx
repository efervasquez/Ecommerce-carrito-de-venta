import React, { useState } from 'react';
import { InspeccionInput, InspeccionResponse, registrarInspeccion } from './api';

export const InspeccionCampo: React.FC = () => {
  const [reclamoId, setReclamoId] = useState('');
  const [resultado, setResultado] = useState<'conforme' | 'falla'>('conforme');
  const [comprobante, setComprobante] = useState(false);
  const [pertenencia, setPertenencia] = useState(false);
  const [defecto, setDefecto] = useState(false);
  const [motivoFalla, setMotivoFalla] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMensaje(null);
    setError(null);
    setEnviando(true);
    const payload: InspeccionInput = {
      resultado,
      comprobante_verificado: comprobante,
      pertenencia_botica_verificada: pertenencia,
      defecto_fisico_verificado: defecto,
      ...(resultado === 'falla' ? { motivo_falla: motivoFalla } : {}),
      ...(observaciones ? { observaciones } : {}),
    };
    try {
      const respuesta: InspeccionResponse = await registrarInspeccion(
        Number(reclamoId),
        payload,
      );
      setMensaje(
        `${respuesta.mensaje}${
          respuesta.intentos_restantes !== undefined
            ? ` Intentos restantes: ${respuesta.intentos_restantes}.`
            : ''
        }`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar la inspección.');
    } finally {
      setEnviando(false);
    }
  };

  const puedeEnviar = Number.isInteger(Number(reclamoId)) && Number(reclamoId) > 0;

  return (
    <section style={styles.card} aria-labelledby="inspeccion-title">
      <h2 id="inspeccion-title" style={styles.subtitle}>
        Validación física en campo
      </h2>
      <p style={styles.help}>
        Valida presencialmente los 3 requisitos antes de confirmar el cambio físico.
      </p>
      <form onSubmit={handleSubmit} style={styles.form} noValidate>
        <label htmlFor="reclamo-id" style={styles.label}>
          ID del reclamo
        </label>
        <input
          id="reclamo-id"
          name="reclamo_id"
          type="number"
          min="1"
          value={reclamoId}
          onChange={(event) => setReclamoId(event.target.value)}
          style={styles.input}
        />

        <label htmlFor="resultado" style={styles.label}>
          Resultado de la inspección
        </label>
        <select
          id="resultado"
          name="resultado"
          value={resultado}
          onChange={(event) => setResultado(event.target.value as 'conforme' | 'falla')}
          style={styles.input}
        >
          <option value="conforme">Conforme</option>
          <option value="falla">Falla</option>
        </select>

        <fieldset style={styles.fieldset}>
          <legend style={styles.legend}>Requisitos verificados</legend>
          <label htmlFor="comprobante-verificado" style={styles.check}>
            <input
              id="comprobante-verificado"
              name="comprobante_verificado"
              type="checkbox"
              checked={comprobante}
              onChange={(event) => setComprobante(event.target.checked)}
            />
            Comprobante original verificado
          </label>
          <label htmlFor="pertenencia-verificada" style={styles.check}>
            <input
              id="pertenencia-verificada"
              name="pertenencia_botica_verificada"
              type="checkbox"
              checked={pertenencia}
              onChange={(event) => setPertenencia(event.target.checked)}
            />
            Pertenencia a Botica la Luz verificada
          </label>
          <label htmlFor="defecto-verificado" style={styles.check}>
            <input
              id="defecto-verificado"
              name="defecto_fisico_verificado"
              type="checkbox"
              checked={defecto}
              onChange={(event) => setDefecto(event.target.checked)}
            />
            Defecto físico verificado
          </label>
        </fieldset>

        {resultado === 'falla' && (
          <>
            <label htmlFor="motivo-falla" style={styles.label}>
              Motivo de la falla
            </label>
            <input
              id="motivo-falla"
              name="motivo_falla"
              type="text"
              value={motivoFalla}
              onChange={(event) => setMotivoFalla(event.target.value)}
              style={styles.input}
              required
            />
          </>
        )}

        <label htmlFor="observaciones" style={styles.label}>
          Observaciones
        </label>
        <textarea
          id="observaciones"
          name="observaciones"
          value={observaciones}
          onChange={(event) => setObservaciones(event.target.value)}
          style={styles.textarea}
        />

        <button
          type="submit"
          disabled={!puedeEnviar || enviando}
          style={styles.primary}
        >
          Registrar inspección
        </button>
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
    </section>
  );
};

const styles: Record<string, React.CSSProperties> = {
  card: {
    maxWidth: 900,
    margin: '0.75rem auto',
    padding: '1rem',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  subtitle: { fontSize: '1.15rem', color: '#1e293b' },
  help: { color: '#64748b', fontSize: '0.9rem' },
  form: { display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: 520 },
  label: { fontWeight: 600, color: '#334155' },
  input: { padding: '0.45rem', border: '1px solid #cbd5e1', borderRadius: 4 },
  textarea: {
    padding: '0.45rem',
    border: '1px solid #cbd5e1',
    borderRadius: 4,
    minHeight: 70,
  },
  fieldset: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
    border: '1px solid #e2e8f0',
    borderRadius: 6,
    padding: '0.6rem',
  },
  legend: { fontWeight: 600, color: '#334155' },
  check: { display: 'flex', gap: '0.45rem', alignItems: 'center', color: '#334155' },
  primary: {
    alignSelf: 'flex-start',
    padding: '0.55rem 0.9rem',
    border: 0,
    borderRadius: 5,
    background: '#0f766e',
    color: '#fff',
    fontWeight: 700,
  },
  message: {
    marginTop: '0.75rem',
    padding: '0.6rem',
    background: '#ecfdf5',
    color: '#047857',
    borderRadius: 5,
  },
  error: {
    marginTop: '0.75rem',
    padding: '0.6rem',
    background: '#fef2f2',
    color: '#b91c1c',
    borderRadius: 5,
  },
};
