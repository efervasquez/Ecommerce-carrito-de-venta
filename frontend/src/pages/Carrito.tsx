import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  CartItem,
  CartResponse,
  checkoutCart,
  deleteCartItem,
  getCart,
  updateCartItem,
} from '../services/cart';

export const Carrito: React.FC = () => {
  const queryClient = useQueryClient();
  const cartQuery = useQuery({ queryKey: ['carrito'], queryFn: getCart });
  const [message, setMessage] = useState<string | null>(null);

  const updateMutation = useMutation({
    mutationFn: ({ productId, quantity }: { productId: number; quantity: number }) =>
      updateCartItem(productId, quantity),
    onSuccess: (data: CartResponse) => queryClient.setQueryData(['carrito'], data),
    onError: (error: Error) => setMessage(error.message),
  });
  const deleteMutation = useMutation({
    mutationFn: (productId: number) => deleteCartItem(productId),
    onSuccess: (data: CartResponse) => queryClient.setQueryData(['carrito'], data),
    onError: (error: Error) => setMessage(error.message),
  });
  const checkoutMutation = useMutation({
    mutationFn: checkoutCart,
    onSuccess: (data) => {
      queryClient.setQueryData<CartResponse>(['carrito'], (current) =>
        current ? { ...current, reserva_expira_en: data.reserva_expira_en } : current,
      );
      setMessage(`${data.message} Reserva expira en ${formatDate(data.reserva_expira_en)}.`);
    },
    onError: (error: Error) => setMessage(error.message),
  });

  if (cartQuery.isLoading) return <p role="status" style={styles.status}>Cargando carrito...</p>;
  if (cartQuery.isError) return <p role="alert" style={styles.error}>{cartQuery.error.message}</p>;
  const cart = cartQuery.data;
  if (!cart) return null;

  const renderItem = (item: CartItem) => (
    <article key={item.producto_id} style={styles.item}>
      <img src={item.imagen_url ?? 'https://placehold.co/160x120?text=Producto'} alt={item.nombre} style={styles.image} />
      <div style={styles.itemContent}>
        <Link to={`/catalogo/productos/${item.producto_id}`} style={styles.name}>{item.nombre}</Link>
        <p style={styles.itemText}>{item.precio_final.toFixed(2)} PEN · Stock: {item.stock_disponible}</p>
        {item.descuento_porcentaje > 0 && <p style={styles.offer}>{item.descuento_porcentaje}% DSCTO</p>}
        <div style={styles.controls}>
          <label htmlFor={`cantidad-${item.producto_id}`}>Cantidad</label>
          <input
            id={`cantidad-${item.producto_id}`}
            type="number"
            min="1"
            max={item.stock_disponible}
            value={item.cantidad}
            onChange={(event) => {
              const quantity = Number(event.target.value);
              if (Number.isInteger(quantity) && quantity >= 1) {
                updateMutation.mutate({ productId: item.producto_id, quantity });
              }
            }}
            style={styles.quantity}
          />
          <button type="button" onClick={() => deleteMutation.mutate(item.producto_id)} style={styles.deleteButton}>
            Eliminar
          </button>
        </div>
        <p style={styles.subtotal}>Subtotal: {item.subtotal.toFixed(2)} PEN</p>
      </div>
    </article>
  );

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.title}>Carrito</h1>
        <Link to="/catalogo" style={styles.link}>Seguir comprando</Link>
      </header>
      {message && <p role="status" style={styles.message}>{message}</p>}
      {cart.reserva_expira_en && (
        <p role="status" style={styles.expiration}>Reserva expira en {formatDate(cart.reserva_expira_en)}</p>
      )}

      <section aria-labelledby="ofertas-title">
        <h2 id="ofertas-title">Productos en Oferta</h2>
        {cart.items_oferta.length === 0 ? <p>No hay productos en oferta.</p> : cart.items_oferta.map(renderItem)}
      </section>
      <section aria-labelledby="regulares-title">
        <h2 id="regulares-title">Productos regulares</h2>
        {cart.items_regulares.length === 0 ? <p>No hay productos regulares.</p> : cart.items_regulares.map(renderItem)}
      </section>

      <aside style={styles.summary} aria-label="Resumen del carrito">
        <p>Subtotal: <strong>{cart.subtotal.toFixed(2)} PEN</strong></p>
        <p>Ahorro total: <strong>{cart.ahorro_total.toFixed(2)} PEN</strong></p>
        <p>Total: <strong>{cart.total.toFixed(2)} PEN</strong></p>
        <button
          type="button"
          disabled={cart.items_oferta.length + cart.items_regulares.length === 0 || checkoutMutation.isPending}
          onClick={() => checkoutMutation.mutate()}
          style={styles.checkout}
        >
          Reservar y continuar
        </button>
      </aside>
    </main>
  );
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#f8fafc', padding: '1rem', fontFamily: 'system-ui, -apple-system, sans-serif' },
  header: { maxWidth: 900, margin: '0 auto 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  title: { color: '#1e293b' },
  link: { color: '#2563eb', fontWeight: 600 },
  item: { maxWidth: 900, margin: '0.75rem auto', padding: '1rem', display: 'flex', gap: '1rem', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8 },
  image: { width: 110, height: 85, objectFit: 'cover', borderRadius: 6, background: '#f1f5f9' },
  itemContent: { flex: 1 },
  name: { color: '#1e293b', fontWeight: 700, textDecoration: 'none' },
  itemText: { color: '#64748b' },
  offer: { color: '#b45309', fontWeight: 700 },
  controls: { display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' },
  quantity: { width: 70, padding: '0.4rem', border: '1px solid #cbd5e1', borderRadius: 4 },
  deleteButton: { padding: '0.45rem 0.7rem', border: 0, borderRadius: 4, background: '#fee2e2', color: '#b91c1c', fontWeight: 600 },
  subtotal: { fontWeight: 700 },
  summary: { maxWidth: 900, margin: '1rem auto', padding: '1rem', background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8 },
  checkout: { padding: '0.7rem 1rem', border: 0, borderRadius: 5, background: '#0f766e', color: '#fff', fontWeight: 700 },
  expiration: { maxWidth: 900, margin: '0 auto', color: '#b45309', fontWeight: 700 },
  message: { maxWidth: 900, margin: '0 auto', padding: '0.65rem', background: '#ecfdf5', color: '#047857', borderRadius: 5 },
  error: { padding: '1rem', color: '#b91c1c' },
  status: { padding: '2rem', color: '#475569' },
};

export default Carrito;
