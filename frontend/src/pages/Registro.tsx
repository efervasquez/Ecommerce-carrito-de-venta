import React, { useState } from 'react';
import { ApiError, solicitarRegistro } from '../services/auth';

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export const Registro: React.FC = () => {
  const [email, setEmail] = useState('');
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMensaje(null);
    setError(null);

    const emailNormalizado = email.trim();
    if (!emailNormalizado) {
      setError('El campo email es requerido.');
      return;
    }
    if (!EMAIL_RE.test(emailNormalizado)) {
      setError('Formato de correo electrónico inválido');
      return;
    }

    setEnviando(true);
    try {
      const response = await solicitarRegistro(emailNormalizado);
      setMensaje(response.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Error al procesar la solicitud.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main style={styles.container}>
      <form onSubmit={handleSubmit} style={styles.form} noValidate>
        <h1 style={styles.title}>Crear cuenta</h1>

        <label htmlFor="email" style={styles.label}>
          Correo electrónico
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          style={styles.input}
        />

        {error && (
          <p role="alert" style={styles.error}>
            {error}
          </p>
        )}

        {mensaje && <p style={styles.mensaje}>{mensaje}</p>}

        <button type="submit" disabled={enviando} style={styles.button}>
          Registrarme
        </button>

        <p style={styles.enlace}>
          ¿Ya tienes cuenta?{' '}
          <a href="/login" style={styles.link}>
            Inicia sesión
          </a>
        </p>
      </form>
    </main>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f8fafc',
    padding: '1rem',
  },
  form: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#ffffff',
    padding: '2rem',
    borderRadius: 8,
    border: '1px solid #e2e8f0',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  title: {
    marginTop: 0,
    fontSize: '1.4rem',
    color: '#1e293b',
  },
  label: {
    display: 'block',
    marginBottom: '0.5rem',
    fontWeight: 600,
    color: '#334155',
  },
  input: {
    width: '100%',
    padding: '0.6rem',
    borderRadius: 4,
    border: '1px solid #cbd5e1',
    fontSize: '1rem',
    boxSizing: 'border-box',
  },
  error: {
    color: '#ef4444',
    backgroundColor: '#fef2f2',
    padding: '0.6rem',
    borderRadius: 4,
    margin: '0.75rem 0 0',
  },
  mensaje: {
    color: '#047857',
    backgroundColor: '#ecfdf5',
    padding: '0.6rem',
    borderRadius: 4,
    margin: '0.75rem 0 0',
  },
  button: {
    marginTop: '1rem',
    width: '100%',
    padding: '0.6rem 1rem',
    backgroundColor: '#2563eb',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '1rem',
  },
  enlace: {
    marginTop: '1rem',
    textAlign: 'center',
    color: '#64748b',
    fontSize: '0.9rem',
  },
  link: {
    color: '#2563eb',
  },
};

export default Registro;
