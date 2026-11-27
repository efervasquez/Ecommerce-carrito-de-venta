import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { getPedido } from '../services/pagos';

export const Confirmacion: React.FC = () => {
  const { numero = '' } = useParams<{ numero: string }>();
  const pedidoQuery = useQuery({
    queryKey: ['pedido', numero],
    queryFn: () => getPedido(numero),
    enabled: Boolean(numero),
  });

  if (pedidoQuery.isLoading) return <p role="status">Cargando pedido...</p>;
  if (pedidoQuery.isError) return <p role="alert">{pedidoQuery.error.message}</p>;
  const pedido = pedidoQuery.data;
  if (!pedido) return null;

  return (
    <main style={styles.page}>
      <h1>¡Pago confirmado!</h1>
      <p>{`#${pedido.numero}`}</p>
      <p>{`S/ ${pedido.monto.toFixed(2)}`}</p>
      <p>Estado: {pedido.estado}</p>
      <p>Entrega: {pedido.entrega} ({pedido.metodo_entrega})</p>
      <ul>
        {pedido.items.map((item) => (
          <li key={item.producto_id}>
            {item.nombre} x {item.cantidad} — S/ {item.subtotal.toFixed(2)}
          </li>
        ))}
      </ul>
      <Link to="/catalogo">Seguir comprando</Link>
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
};

export default Confirmacion;
