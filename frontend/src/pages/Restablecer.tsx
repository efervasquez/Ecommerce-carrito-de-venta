import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ApiError, restablecerContrasena } from '../services/auth';

export const Restablecer: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [enlaceInvalido, setEnlaceInvalido] = useState(false);

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
      const response = await restablecerContrasena(token, password);
      setMensaje(response.message);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setEnlaceInvalido(true);
        setError('El enlace de recuperación es inválido o ha expirado');
      } else {
        setError(err instanceof ApiError ? err.detail : 'Error al restablecer la contraseña.');
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main style={styles.container}>
      <section style={styles.form}>
        <h1 style={styles.title}>Restablecer contraseña</h1>

        {enlaceInvalido ? (
          <>
            <p role="alert" style={styles.error}>{error}</p>
            <Link to="/recuperar" style={styles.buttonLink}>Solicitar nuevo enlace</Link>
          </>
        ) : mensaje ? (
          <>
            <p style={styles.mensaje}>{mensaje}</p>
            <Link to="/login" style={styles.buttonLink}>Ir a iniciar sesión</Link>
          </>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <label htmlFor="password" style={styles.label}>Nueva contraseña</label>
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

            {error && <p role="alert" style={styles.error}>{error}</p>}
            <button type="submit" disabled={enviando} style={styles.button}>
              Actualizar contraseña
            </button>
          </form>
        )}
      </section>
    </main>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
    backgroundColor: '#f8fafc', padding: '1rem',
  },
  form: {
    width: '100%', maxWidth: 420, backgroundColor: '#ffffff', padding: '2rem',
    borderRadius: 8, border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  title: { marginTop: 0, fontSize: '1.4rem', color: '#1e293b' },
  label: { display: 'block', marginBottom: '0.5rem', fontWeight: 600, color: '#334155' },
  input: { width: '100%', padding: '0.6rem', borderRadius: 4, border: '1px solid #cbd5e1', fontSize: '1rem', boxSizing: 'border-box' },
  error: { color: '#ef4444', backgroundColor: '#fef2f2', padding: '0.6rem', borderRadius: 4, margin: '0.75rem 0 0' },
  mensaje: { color: '#047857', backgroundColor: '#ecfdf5', padding: '0.6rem', borderRadius: 4, margin: '0.75rem 0 0' },
  button: { marginTop: '1rem', width: '100%', padding: '0.6rem 1rem', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 500, fontSize: '1rem' },
  buttonLink: { display: 'block', marginTop: '1rem', padding: '0.6rem 1rem', backgroundColor: '#2563eb', color: '#fff', borderRadius: 4, textDecoration: 'none', textAlign: 'center', fontWeight: 500 },
};

export default Restablecer;
