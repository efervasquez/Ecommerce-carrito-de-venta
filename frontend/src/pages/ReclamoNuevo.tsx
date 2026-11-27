import React, { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  crearReclamo,
  getPedido,
  PedidoItemOpcion,
  ReclamoRegistro,
} from '../modules/reclamos/api';

export const ReclamoNuevo: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [pedidoNumero, setPedidoNumero] = useState(
    searchParams.get('pedido_numero') ?? '',
  );
  const [productoId, setProductoId] = useState('');
  const [motivo, setMotivo] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [fotoProducto, setFotoProducto] = useState<File | null>(null);
  const [fotoComprobante, setFotoComprobante] = useState<File | null>(null);
  const [registro, setRegistro] = useState<ReclamoRegistro | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<PedidoItemOpcion[]>([]);
  const [cargandoItems, setCargandoItems] = useState(false);
  const [errorItems, setErrorItems] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const cargarProductos = useCallback(async (numeroPedido: string) => {
    const numero = numeroPedido.trim();
    if (!numero) {
      setErrorItems('Ingresa el número de pedido para cargar sus productos.');
      return;
    }
    setCargandoItems(true);
    setErrorItems(null);
    try {
      const pedido = await getPedido(numero);
      const opciones = Array.isArray(pedido.items) ? pedido.items : [];
      setItems(opciones);
      setProductoId((actual) => actual || (opciones[0] ? String(opciones[0].producto_id) : ''));
    } catch (err) {
      setItems([]);
      setProductoId('');
      setErrorItems(
        err instanceof Error ? err.message : 'No se pudieron cargar los productos del pedido.',
      );
    } finally {
      setCargandoItems(false);
    }
  }, []);

  useEffect(() => {
    const inicial = searchParams.get('pedido_numero');
    if (inicial) {
      void cargarProductos(inicial);
    }
  }, []);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setRegistro(null);

    if (!fotoProducto) {
      setError('La fotografía del producto dañado es obligatoria.');
      return;
    }
    if (!fotoComprobante) {
      setError('La fotografía o archivo del comprobante de pago es obligatoria.');
      return;
    }

    setEnviando(true);
    try {
      const respuesta = await crearReclamo({
        pedido_numero: pedidoNumero.trim(),
        producto_id: Number(productoId),
        motivo: motivo.trim(),
        descripcion: descripcion.trim() || undefined,
        foto_producto: fotoProducto,
        foto_comprobante: fotoComprobante,
      });
      setRegistro(respuesta);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar el reclamo.');
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main style={styles.page}>
      <section style={styles.card}>
        <h1 style={styles.title}>Registrar reclamo</h1>
        <p style={styles.help}>
          Solo proceden reclamos por productos dañados o en mal estado. La botica no
          realiza devoluciones de dinero: la solución es la reposición física del producto.
        </p>

        <form onSubmit={handleSubmit} style={styles.form} noValidate>
          <label htmlFor="pedido-numero" style={styles.label}>
            Número de pedido
          </label>
          <input
            id="pedido-numero"
            name="pedido_numero"
            type="text"
            value={pedidoNumero}
            onChange={(event) => setPedidoNumero(event.target.value)}
            placeholder="BL-..."
            style={styles.input}
          />

          <button
            type="button"
            onClick={() => void cargarProductos(pedidoNumero)}
            disabled={cargandoItems}
            style={styles.secondary}
          >
            Cargar productos del pedido
          </button>
          {errorItems && (
            <p role="alert" style={styles.error}>
              {errorItems}
            </p>
          )}

          <label htmlFor="producto-id" style={styles.label}>
            Producto del pedido
          </label>
          <select
            id="producto-id"
            name="producto_id"
            value={productoId}
            onChange={(event) => setProductoId(event.target.value)}
            style={styles.input}
            disabled={items.length === 0}
          >
            <option value="">
              {cargandoItems
                ? 'Cargando productos...'
                : items.length === 0
                  ? 'Carga los productos del pedido'
                  : 'Selecciona un producto'}
            </option>
            {items.map((item) => (
              <option key={item.producto_id} value={item.producto_id}>
                {item.nombre} (ID {item.producto_id})
              </option>
            ))}
          </select>

          <label htmlFor="motivo" style={styles.label}>
            Motivo
          </label>
          <input
            id="motivo"
            name="motivo"
            type="text"
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            placeholder="Producto dañado"
            style={styles.input}
          />

          <label htmlFor="descripcion" style={styles.label}>
            Descripción
          </label>
          <textarea
            id="descripcion"
            name="descripcion"
            value={descripcion}
            onChange={(event) => setDescripcion(event.target.value)}
            placeholder="Frasco quebrado al abrir el empaque"
            style={styles.textarea}
          />

          <label htmlFor="foto-producto" style={styles.label}>
            Fotografía del producto dañado
          </label>
          <input
            id="foto-producto"
            name="foto_producto"
            type="file"
            accept="image/jpeg,image/png"
            onChange={(event) => setFotoProducto(event.target.files?.[0] ?? null)}
            style={styles.input}
          />

          <label htmlFor="foto-comprobante" style={styles.label}>
            Fotografía o archivo del comprobante de pago
          </label>
          <input
            id="foto-comprobante"
            name="foto_comprobante"
            type="file"
            accept="image/jpeg,image/png,application/pdf"
            onChange={(event) => setFotoComprobante(event.target.files?.[0] ?? null)}
            style={styles.input}
          />

          <button type="submit" disabled={enviando} style={styles.primary}>
            Registrar reclamo
          </button>
        </form>

        {registro && (
          <div role="status" style={styles.success}>
            <p>Reclamo registrado con estado {registro.estado}.</p>
            <p>
              Pedido de reposición generado: <strong>{registro.pedido_reposicion_numero}</strong>
            </p>
          </div>
        )}
        {error && (
          <p role="alert" style={styles.error}>
            {error}
          </p>
        )}

        <p style={styles.enlace}>
          <Link to="/reclamos" style={styles.link}>
            Ver mis reclamos
          </Link>
        </p>
      </section>
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
  card: {
    maxWidth: 560,
    margin: '1rem auto',
    padding: '1.5rem',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
  },
  title: { marginTop: 0, color: '#1e293b', fontSize: '1.4rem' },
  help: { color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5 },
  form: { display: 'flex', flexDirection: 'column', gap: '0.45rem' },
  label: { fontWeight: 600, color: '#334155', marginTop: '0.35rem' },
  input: { padding: '0.55rem', border: '1px solid #cbd5e1', borderRadius: 4 },
  textarea: {
    padding: '0.55rem',
    border: '1px solid #cbd5e1',
    borderRadius: 4,
    minHeight: 80,
  },
  secondary: {
    alignSelf: 'flex-start',
    marginTop: '0.35rem',
    padding: '0.4rem 0.7rem',
    border: '1px solid #cbd5e1',
    borderRadius: 4,
    background: '#f8fafc',
    color: '#334155',
  },
  primary: {
    marginTop: '0.75rem',
    padding: '0.6rem 1rem',
    border: 0,
    borderRadius: 5,
    background: '#2563eb',
    color: '#fff',
    fontWeight: 700,
  },
  success: {
    marginTop: '1rem',
    padding: '0.75rem',
    background: '#ecfdf5',
    color: '#047857',
    borderRadius: 5,
  },
  error: {
    marginTop: '1rem',
    padding: '0.75rem',
    background: '#fef2f2',
    color: '#b91c1c',
    borderRadius: 5,
  },
  enlace: { marginTop: '1rem' },
  link: { color: '#2563eb' },
};

export default ReclamoNuevo;
