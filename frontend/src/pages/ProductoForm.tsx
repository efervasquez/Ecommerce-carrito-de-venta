import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  actualizarProducto,
  crearProducto,
  getProducto,
  METODOS_ENTREGA,
  ProductoPayload,
} from './BackofficeInventario';

export const ProductoForm: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const editando = Boolean(id);

  const [nombre, setNombre] = useState('');
  const [componentes, setComponentes] = useState('');
  const [precioRegular, setPrecioRegular] = useState('');
  const [moneda, setMoneda] = useState('PEN');
  const [descuento, setDescuento] = useState('0');
  const [presentacion, setPresentacion] = useState('');
  const [detalle, setDetalle] = useState('');
  const [imagenUrl, setImagenUrl] = useState('');
  const [contraindicaciones, setContraindicaciones] = useState('');
  const [precauciones, setPrecauciones] = useState('');
  const [reacciones, setReacciones] = useState('');
  const [stockInicial, setStockInicial] = useState('0');
  const [metodos, setMetodos] = useState<string[]>([...METODOS_ENTREGA]);
  const [preciosBajos, setPreciosBajos] = useState(false);
  const [requiereReceta, setRequiereReceta] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const productoQuery = useQuery({
    queryKey: ['inventario-producto', id],
    queryFn: () => getProducto(Number(id)),
    enabled: editando,
  });

  useEffect(() => {
    const producto = productoQuery.data;
    if (!producto) return;
    setNombre(producto.nombre);
    setComponentes(producto.componentes);
    setPrecioRegular(String(producto.precio_regular));
    setMoneda(producto.moneda);
    setDescuento(String(producto.descuento_porcentaje));
    setPresentacion(producto.presentacion);
    setDetalle(producto.detalle);
    setImagenUrl(producto.imagen_url ?? '');
    setContraindicaciones(producto.contraindicaciones ?? '');
    setPrecauciones(producto.precauciones_advertencias ?? '');
    setReacciones(producto.reacciones_adversas ?? '');
    setMetodos(producto.metodos_entrega ?? []);
    setPreciosBajos(producto.precios_bajos);
    setRequiereReceta(producto.requiere_receta);
  }, [productoQuery.data]);

  const alternarMetodo = (metodo: string) => {
    setMetodos((actual) =>
      actual.includes(metodo)
        ? actual.filter((valor) => valor !== metodo)
        : [...actual, metodo],
    );
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    const payload: ProductoPayload = {
      nombre: nombre.trim(),
      componentes: componentes.trim(),
      precio_regular: Number(precioRegular),
      moneda: moneda.trim() || 'PEN',
      descuento_porcentaje: Number(descuento),
      precios_bajos: preciosBajos,
      requiere_receta: requiereReceta,
      presentacion: presentacion.trim(),
      detalle: detalle.trim(),
      imagen_url: imagenUrl.trim() || undefined,
      metodos_entrega: metodos,
      contraindicaciones: contraindicaciones.trim(),
      precauciones_advertencias: precauciones.trim(),
      reacciones_adversas: reacciones.trim(),
    };
    setGuardando(true);
    try {
      if (editando) {
        await actualizarProducto(Number(id), payload);
      } else {
        await crearProducto({ ...payload, stock_disponible: Number(stockInicial) });
      }
      navigate('/backoffice/inventario');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar el producto.');
    } finally {
      setGuardando(false);
    }
  };

  if (editando && productoQuery.isLoading) {
    return <p role="status" style={styles.status}>Cargando producto...</p>;
  }
  if (editando && productoQuery.isError) {
    return (
      <p role="alert" style={styles.error}>
        {(productoQuery.error as Error).message}
      </p>
    );
  }

  return (
    <main style={styles.page}>
      <section style={styles.card}>
        <h1 style={styles.title}>
          {editando ? 'Editar producto' : 'Nuevo producto'}
        </h1>
        <p style={styles.help}>
          Mantén la ficha comercial, clínica y sanitaria actualizada para la operación
          de contingencia.
        </p>

        <form onSubmit={handleSubmit} style={styles.form} noValidate>
          <label htmlFor="nombre" style={styles.label}>Nombre</label>
          <input
            id="nombre"
            name="nombre"
            type="text"
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
            style={styles.input}
          />

          <label htmlFor="componentes" style={styles.label}>Componentes</label>
          <input
            id="componentes"
            name="componentes"
            type="text"
            value={componentes}
            onChange={(event) => setComponentes(event.target.value)}
            style={styles.input}
          />

          <label htmlFor="precio_regular" style={styles.label}>Precio regular</label>
          <input
            id="precio_regular"
            name="precio_regular"
            type="number"
            step="0.01"
            min="0"
            value={precioRegular}
            onChange={(event) => setPrecioRegular(event.target.value)}
            style={styles.input}
          />

          <label htmlFor="moneda" style={styles.label}>Moneda</label>
          <input
            id="moneda"
            name="moneda"
            type="text"
            value={moneda}
            onChange={(event) => setMoneda(event.target.value)}
            style={styles.input}
          />

          <label htmlFor="descuento_porcentaje" style={styles.label}>
            Descuento (%)
          </label>
          <input
            id="descuento_porcentaje"
            name="descuento_porcentaje"
            type="number"
            step="0.01"
            min="0"
            max="100"
            value={descuento}
            onChange={(event) => setDescuento(event.target.value)}
            style={styles.input}
          />

          <label htmlFor="presentacion" style={styles.label}>Presentación</label>
          <input
            id="presentacion"
            name="presentacion"
            type="text"
            value={presentacion}
            onChange={(event) => setPresentacion(event.target.value)}
            style={styles.input}
          />

          <label htmlFor="detalle" style={styles.label}>Detalle</label>
          <textarea
            id="detalle"
            name="detalle"
            value={detalle}
            onChange={(event) => setDetalle(event.target.value)}
            style={styles.textarea}
          />

          <label htmlFor="imagen_url" style={styles.label}>Imagen URL</label>
          <input
            id="imagen_url"
            name="imagen_url"
            type="text"
            value={imagenUrl}
            onChange={(event) => setImagenUrl(event.target.value)}
            style={styles.input}
          />

          <fieldset style={styles.fieldset}>
            <legend style={styles.legend}>Métodos de entrega</legend>
            {METODOS_ENTREGA.map((metodo) => (
              <label key={metodo} htmlFor={`metodo-${metodo}`} style={styles.check}>
                <input
                  id={`metodo-${metodo}`}
                  name="metodos_entrega"
                  type="checkbox"
                  value={metodo}
                  checked={metodos.includes(metodo)}
                  onChange={() => alternarMetodo(metodo)}
                />
                {metodo === 'delivery' ? 'Delivery' : 'Retiro en botica'}
              </label>
            ))}
          </fieldset>

          <label htmlFor="precios_bajos" style={styles.check}>
            <input
              id="precios_bajos"
              name="precios_bajos"
              type="checkbox"
              checked={preciosBajos}
              onChange={(event) => setPreciosBajos(event.target.checked)}
            />
            Precios bajos
          </label>

          <label htmlFor="requiere_receta" style={styles.check}>
            <input
              id="requiere_receta"
              name="requiere_receta"
              type="checkbox"
              checked={requiereReceta}
              onChange={(event) => setRequiereReceta(event.target.checked)}
            />
            Requiere receta
          </label>

          {!editando && (
            <>
              <label htmlFor="stock_disponible" style={styles.label}>
                Stock inicial
              </label>
              <input
                id="stock_disponible"
                name="stock_disponible"
                type="number"
                min="0"
                step="1"
                value={stockInicial}
                onChange={(event) => setStockInicial(event.target.value)}
                style={styles.input}
              />
            </>
          )}

          <label htmlFor="contraindicaciones" style={styles.label}>
            Contraindicaciones
          </label>
          <textarea
            id="contraindicaciones"
            name="contraindicaciones"
            value={contraindicaciones}
            onChange={(event) => setContraindicaciones(event.target.value)}
            style={styles.textarea}
          />

          <label htmlFor="precauciones_advertencias" style={styles.label}>
            Precauciones y advertencias
          </label>
          <textarea
            id="precauciones_advertencias"
            name="precauciones_advertencias"
            value={precauciones}
            onChange={(event) => setPrecauciones(event.target.value)}
            style={styles.textarea}
          />

          <label htmlFor="reacciones_adversas" style={styles.label}>
            Reacciones adversas
          </label>
          <textarea
            id="reacciones_adversas"
            name="reacciones_adversas"
            value={reacciones}
            onChange={(event) => setReacciones(event.target.value)}
            style={styles.textarea}
          />

          <button type="submit" disabled={guardando} style={styles.primary}>
            {editando ? 'Guardar cambios' : 'Guardar producto'}
          </button>
        </form>

        {error && (
          <p role="alert" style={styles.error}>
            {error}
          </p>
        )}

        <p style={styles.enlace}>
          <Link to="/backoffice/inventario" style={styles.link}>
            Volver al inventario
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
    maxWidth: 680,
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
    minHeight: 70,
  },
  fieldset: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
    border: '1px solid #e2e8f0',
    borderRadius: 6,
    padding: '0.6rem',
    marginTop: '0.35rem',
  },
  legend: { fontWeight: 600, color: '#334155' },
  check: { display: 'flex', gap: '0.45rem', alignItems: 'center', color: '#334155' },
  primary: {
    marginTop: '0.75rem',
    padding: '0.6rem 1rem',
    border: 0,
    borderRadius: 5,
    background: '#2563eb',
    color: '#fff',
    fontWeight: 700,
  },
  error: {
    marginTop: '1rem',
    padding: '0.75rem',
    background: '#fef2f2',
    color: '#b91c1c',
    borderRadius: 5,
  },
  status: { padding: '2rem', color: '#475569' },
  enlace: { marginTop: '1rem' },
  link: { color: '#2563eb' },
};

export default ProductoForm;
