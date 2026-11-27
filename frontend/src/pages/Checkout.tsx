import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { loadStripe } from '@stripe/stripe-js';
import { CardElement, Elements, useElements, useStripe } from '@stripe/react-stripe-js';
import { Link } from 'react-router-dom';
import { getCart } from '../services/cart';
import {
  createDireccion,
  getDirecciones,
  getPagoEstado,
  getZonas,
  iniciarCheckout,
  PedidoResumen,
} from '../services/pagos';

const MSG_INSUFFICIENT =
  'Su pago fue rechazado por saldo insuficiente. Por favor intente con otra tarjeta';
const MSG_OTHER = 'El pago no pudo procesarse. Por favor intente con otra tarjeta';

const stripePromise = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_test_placeholder',
);

const esperar = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

interface FormProps {
  total: number;
  nombreProducto: string | null;
  recargarCarrito: () => void;
  onConfirmado: (pedido: PedidoResumen) => void;
}

const CheckoutForm: React.FC<FormProps> = ({
  total,
  nombreProducto,
  recargarCarrito,
  onConfirmado,
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const zonasQuery = useQuery({ queryKey: ['zonas'], queryFn: getZonas });
  const direccionesQuery = useQuery({ queryKey: ['direcciones'], queryFn: getDirecciones });
  const [metodo, setMetodo] = useState<'retiro' | 'delivery'>('retiro');
  const [zonaId, setZonaId] = useState<number | null>(null);
  const [direccionId, setDireccionId] = useState<number | null>(null);
  const [nuevaDireccion, setNuevaDireccion] = useState(false);
  const [linea1, setLinea1] = useState('');
  const [telefono, setTelefono] = useState('');
  const [estado, setEstado] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pagar = async () => {
    setError(null);
    setEstado('Procesando pago...');
    try {
      let idDireccion = direccionId;
      if (metodo === 'delivery' && nuevaDireccion) {
        const zona = zonaId ?? zonasQuery.data?.[0]?.id;
        if (!zona || !linea1 || !telefono) {
          setError('Debe completar la dirección de entrega.');
          setEstado(null);
          return;
        }
        const creada = await createDireccion({
          direccion_linea1: linea1,
          telefono_contacto: telefono,
          zona_id: zona,
        });
        idDireccion = creada.id;
      }
      const checkout = await iniciarCheckout({
        metodo_entrega: metodo,
        ...(metodo === 'delivery' && idDireccion ? { direccion_id: idDireccion } : {}),
      });

      const result = stripe?.confirmCardPayment
        ? await stripe.confirmCardPayment(checkout.client_secret, {
            payment_method: { card: elements?.getElement?.(CardElement) },
          })
        : await stripe?.confirmPayment?.({
            clientSecret: checkout.client_secret,
            elements,
          });

      if (result?.error) {
        const decline = result.error.decline_code ?? result.error.code;
        setError(decline === 'insufficient_funds' ? MSG_INSUFFICIENT : MSG_OTHER);
        setEstado(null);
        recargarCarrito();
        return;
      }

      for (let intento = 0; intento < 20; intento += 1) {
        await esperar(250);
        const estadoPago = await getPagoEstado(checkout.payment_intent_id);
        if (estadoPago.estado === 'confirmado' && estadoPago.pedido) {
          onConfirmado(estadoPago.pedido);
          setEstado(null);
          return;
        }
        if (estadoPago.estado === 'rechazado') {
          setError(MSG_OTHER);
          setEstado(null);
          recargarCarrito();
          return;
        }
      }
      setError(MSG_OTHER);
      setEstado(null);
    } catch (err) {
      setError(err instanceof Error && err.message ? MSG_OTHER : MSG_OTHER);
      setEstado(null);
      recargarCarrito();
    }
  };

  const zonas = zonasQuery.data ?? [];
  const direcciones = direccionesQuery.data ?? [];

  return (
    <section>
      <h1>Finalizar compra</h1>
      {nombreProducto && <p aria-label="producto carrito">{nombreProducto}</p>}
      <p aria-label="total">Total: S/ {total.toFixed(2)}</p>

      <fieldset>
        <legend>Entrega</legend>
        <label>
          <input
            type="radio"
            name="metodo"
            checked={metodo === 'retiro'}
            onChange={() => setMetodo('retiro')}
          />
          En botica
        </label>
        <label>
          <input
            type="radio"
            name="metodo"
            checked={metodo === 'delivery'}
            onChange={() => setMetodo('delivery')}
          />
          A domicilio
        </label>
      </fieldset>

      {metodo === 'delivery' && (
        <div>
          <label htmlFor="zona">Zona</label>
          <select id="zona" value={zonaId ?? ''} onChange={(e) => setZonaId(Number(e.target.value))}>
            <option value="">Seleccione una zona</option>
            {zonas.map((zona) => (
              <option key={zona.id} value={zona.id}>
                {zona.nombre} - {zona.distrito}
              </option>
            ))}
          </select>
          <label htmlFor="direccion">Dirección existente</label>
          <select
            id="direccion"
            value={direccionId ?? ''}
            onChange={(e) => setDireccionId(Number(e.target.value))}
          >
            <option value="">Seleccione una dirección</option>
            {direcciones.map((direccion) => (
              <option key={direccion.id} value={direccion.id}>
                {direccion.direccion_linea1}
              </option>
            ))}
          </select>
          <label>
            <input
              type="checkbox"
              checked={nuevaDireccion}
              onChange={(e) => setNuevaDireccion(e.target.checked)}
            />
            Nueva dirección
          </label>
          {nuevaDireccion && (
            <div>
              <label htmlFor="linea1">Dirección</label>
              <input id="linea1" value={linea1} onChange={(e) => setLinea1(e.target.value)} />
              <label htmlFor="telefono">Teléfono de contacto</label>
              <input id="telefono" value={telefono} onChange={(e) => setTelefono(e.target.value)} />
            </div>
          )}
        </div>
      )}

      <div aria-label="Tarjeta">
        <CardElement />
      </div>
      {estado && <p role="status">{estado}</p>}
      {error && <p role="alert">{error}</p>}
      <button type="button" onClick={pagar} disabled={Boolean(estado)}>
        Pagar ahora
      </button>
      <Link to="/carrito">Volver al carrito</Link>
    </section>
  );
};

export const Checkout: React.FC = () => {
  const cartQuery = useQuery({ queryKey: ['carrito'], queryFn: getCart });
  const [confirmado, setConfirmado] = useState<PedidoResumen | null>(null);
  if (cartQuery.isLoading) return <p role="status">Cargando carrito...</p>;
  const items = [...(cartQuery.data?.items_oferta ?? []), ...(cartQuery.data?.items_regulares ?? [])];
  const nombreProducto = items[0]?.nombre ?? null;
  const total = cartQuery.data?.total ?? 0;

  if (confirmado) {
    return (
      <main>
        <h1>¡Pago confirmado!</h1>
        <p>{`#${confirmado.numero}`}</p>
        <p>{`S/ ${confirmado.monto.toFixed(2)}`}</p>
        <Link to={`/pedidos/${confirmado.numero}`}>Ver detalle del pedido</Link>
      </main>
    );
  }

  return (
    <main>
      <Elements stripe={stripePromise}>
        <CheckoutForm
          total={total}
          nombreProducto={nombreProducto}
          recargarCarrito={() => cartQuery.refetch()}
          onConfirmado={setConfirmado}
        />
      </Elements>
    </main>
  );
};

export default Checkout;
