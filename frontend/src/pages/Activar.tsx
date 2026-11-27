import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { activarCuenta, ApiError } from '../services/auth';

export const Activar: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMensaje(null);
    setError(null);

    if (password !== confirmPassword) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setEnviando(true);
    try {
      await activarCuenta(token, password);
      setMensaje('Cuenta activada exitosamente');
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError('El enlace de activación es inválido o ha expirado');
      } else if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError('Error al activar la cuenta.');
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main style={styles.container}>
      <form onSubmit={handleSubmit} style={styles.form} noValidate>
        <h1 style={styles.title}>Activar cuenta</h1>

        <label htmlFor="password" style={styles.label}>
          Contraseña
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          style={styles.input}
        />

        <label htmlFor="confirm_password" style={{ ...styles.label, marginTop: '0.75rem' }}>
          Confirmar contraseña
        </label>
        <input
          id="confirm_password"
          name="confirm_password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          style={styles.input}
        />

        {error && (
          <p role="alert" style={styles.error}>
            {error}
          </p>
        )}

        {mensaje && <p style={styles.mensaje}>{mensaje}</p>}

        <button type="submit" disabled={enviando} style={styles.button}>
          Activar cuenta
        </button>

        {mensaje && (
          <p style={styles.enlace}>
            <Link to="/login" style={styles.link}>
              Ir a iniciar sesión
            </Link>
          </p>
        )}
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
    fontSize: '0.9rem',
  },
  link: {
    color: '#2563eb',
  },
};

export default Activar;
