import React from 'react';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';

export const Home: React.FC = () => {
  const usuario = useAuthStore((state) => state.usuario);
  const clearSession = useAuthStore((state) => state.clearSession);

  return (
    <main style={styles.container}>
      <h1 style={styles.title}>Botica la Luz</h1>

      {usuario ? (
        <div style={styles.card}>
          <p style={styles.texto}>Sesión iniciada como {usuario.email}</p>
          <button type="button" onClick={clearSession} style={styles.button}>
            Cerrar sesión
          </button>
        </div>
      ) : (
        <div style={styles.card}>
          <Link to="/login" style={styles.buttonLink}>
            Iniciar sesión
          </Link>
          <Link to="/registro" style={styles.buttonLink}>
            Registrarme
          </Link>
        </div>
      )}

      <a href="/catalogo" style={styles.catalogLink}>Explorar catálogo</a>
    </main>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f8fafc',
    padding: '1rem',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  title: {
    fontSize: '1.8rem',
    color: '#1e293b',
  },
  card: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
    alignItems: 'center',
  },
  texto: {
    color: '#334155',
  },
  button: {
    padding: '0.6rem 1rem',
    backgroundColor: '#dc2626',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    fontWeight: 500,
    fontSize: '1rem',
  },
  buttonLink: {
    padding: '0.6rem 1rem',
    backgroundColor: '#2563eb',
    color: '#fff',
    borderRadius: 4,
    textDecoration: 'none',
    fontWeight: 500,
  },
  catalogLink: {
    marginTop: '1rem',
    color: '#2563eb',
    fontWeight: 600,
  },
};

export default Home;
