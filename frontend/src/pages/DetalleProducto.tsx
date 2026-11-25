import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { obtenerProductoDetalle } from '../services/catalog';
import { addCartItem, CartResponse, getCart } from '../services/cart';

export const DetalleProducto: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>();
  const [cantidad, setCantidad] = useState('1');
  const [errorCantidad, setErrorCantidad] = useState<string | null>(null);
  const [cartMessage, setCartMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const cartQuery = useQuery({ queryKey: ['carrito'], queryFn: getCart });
  const addMutation = useMutation({
    mutationFn: (quantity: number) => addCartItem(Number(id), quantity),
    onSuccess: (data: CartResponse) => {
      queryClient.setQueryData(['carrito'], data);
      setCartMessage('Producto agregado al carrito.');
    },
    onError: (error: Error) => setCartMessage(error.message),
  });
  const detailQuery = useQuery({
    queryKey: ['catalogo-producto', id],
    queryFn: () => obtenerProductoDetalle(id),
    enabled: Boolean(id),
  });

  if (detailQuery.isLoading) return <p role="status" style={styles.status}>Cargando producto...</p>;
  if (detailQuery.isError) {
    return (
      <main style={styles.container}>
        <p role="alert" style={styles.error}>{detailQuery.error.message}</p>
        <Link to="/catalogo" style={styles.link}>Volver al catálogo</Link>
      </main>
    );
  }
  if (!detailQuery.data) return null;

  const product = detailQuery.data;
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = Number(cantidad);
    if (!Number.isInteger(parsed) || parsed < 1) {
      setErrorCantidad('La cantidad debe ser un entero mayor o igual a 1.');
      return;
    }
    if (parsed > product.stock_disponible) {
      setErrorCantidad('La cantidad supera el stock disponible.');
      return;
    }
    setErrorCantidad(null);
    addMutation.mutate(parsed);
  };

  return (
    <main style={styles.container}>
      <Link to="/catalogo" style={styles.link}>Volver al catálogo</Link>
      <article style={styles.card}>
        <img
          src={product.imagen_url ?? 'https://placehold.co/800x600?text=Producto'}
          alt={product.nombre}
          style={styles.image}
        />
        <section>
          <h1 style={styles.title}>{product.nombre}</h1>
          <p style={styles.components}>{product.componentes}</p>
          <p style={styles.price}>{product.moneda} {product.precio_regular.toFixed(2)}</p>
          {product.descuento_porcentaje > 0 && <p style={styles.offer}>Oferta -{product.descuento_porcentaje}%</p>}
          {product.precios_bajos && <p style={styles.lowPrice}>Precios bajos</p>}
          <p style={styles.badge}>
            {product.requiere_receta ? 'Necesita receta para la venta' : 'Producto de venta libre'}
          </p>
          <p><strong>Stock disponible:</strong> {product.stock_disponible}</p>
          <p><strong>Presentación:</strong> {product.presentacion}</p>
          <p><strong>Detalle:</strong> {product.detalle}</p>
          <p><strong>Modalidades de entrega:</strong> {product.metodos_entrega.join(', ')}</p>

          <h2 style={styles.sectionTitle}>Contraindicaciones</h2>
          <p>{product.contraindicaciones}</p>
          <h2 style={styles.sectionTitle}>Precauciones/Advertencias</h2>
          <p>{product.precauciones_advertencias}</p>
          <h2 style={styles.sectionTitle}>Reacciones adversas</h2>
          <p>{product.reacciones_adversas}</p>

          <form onSubmit={submit} style={styles.purchaseForm} noValidate>
            <label htmlFor="cantidad">Cantidad</label>
            <input
              id="cantidad"
              name="cantidad"
              type="number"
              min="1"
              max={product.stock_disponible}
              step="1"
              value={cantidad}
              onChange={(event) => setCantidad(event.target.value)}
              style={styles.quantity}
            />
            {errorCantidad && <p role="alert" style={styles.error}>{errorCantidad}</p>}
            <button
              type="submit"
              disabled={product.stock_disponible < 1 || addMutation.isPending}
              style={styles.button}
            >
              Agregar al carrito
            </button>
            {cartMessage && <p aria-live="polite" style={styles.localCart}>{cartMessage}</p>}
            {cartQuery.data && (
              <Link to="/carrito" style={styles.link}>Ver carrito ({cartQuery.data.items_oferta.concat(cartQuery.data.items_regulares).reduce((total, item) => total + item.cantidad, 0)})</Link>
            )}
          </form>
        </section>
      </article>
    </main>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { minHeight: '100vh', background: '#f8fafc', padding: '1rem', fontFamily: 'system-ui, -apple-system, sans-serif' },
  card: { maxWidth: 960, margin: '1rem auto', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '1.25rem', display: 'grid', gridTemplateColumns: 'minmax(240px, 0.8fr) minmax(0, 1.2fr)', gap: '1.5rem' },
  image: { width: '100%', maxHeight: 420, objectFit: 'cover', borderRadius: 8, background: '#f1f5f9' },
  title: { marginTop: 0, color: '#1e293b' },
  components: { color: '#64748b' },
  price: { fontSize: '1.35rem', fontWeight: 700, color: '#0f172a' },
  offer: { color: '#b45309', fontWeight: 700 },
  lowPrice: { color: '#047857', fontWeight: 700 },
  badge: { display: 'inline-block', padding: '0.4rem 0.6rem', borderRadius: 4, background: '#ede9fe', color: '#5b21b6', fontWeight: 600 },
  sectionTitle: { marginBottom: '0.25rem', color: '#334155', fontSize: '1rem' },
  purchaseForm: { marginTop: '1.25rem', borderTop: '1px solid #e2e8f0', paddingTop: '1rem' },
  quantity: { display: 'block', width: 100, marginTop: '0.4rem', padding: '0.55rem', border: '1px solid #cbd5e1', borderRadius: 4 },
  button: { marginTop: '0.75rem', padding: '0.7rem 1rem', border: 0, borderRadius: 5, background: '#0f766e', color: '#fff', fontWeight: 700 },
  localCart: { color: '#047857', fontWeight: 600 },
  error: { color: '#b91c1c', background: '#fef2f2', padding: '0.65rem', borderRadius: 5 },
  status: { padding: '2rem', color: '#475569' },
  link: { color: '#2563eb', fontWeight: 600 },
  productLink: { color: '#1e293b', textDecoration: 'none' },
};

export default DetalleProducto;
