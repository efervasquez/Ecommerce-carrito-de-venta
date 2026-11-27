import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const MSG_INSUFFICIENT =
  'Su pago fue rechazado por saldo insuficiente. Por favor intente con otra tarjeta';
const MSG_OTHER = 'El pago no pudo procesarse. Por favor intente con otra tarjeta';
const ORDER_NUMBER = 'BL-10045';

type StripeHarness = {
  mode: 'ok' | 'insufficient' | 'other';
  pollState: 'procesando' | 'confirmado' | 'rechazado';
};

function harness(): StripeHarness {
  return (globalThis as any).__hu07Harness as StripeHarness;
}

vi.mock(
  '@stripe/stripe-js',
  () => ({
    loadStripe: async () => ({
      confirmPayment: (...args: unknown[]) =>
        (globalThis as any).__hu07Stripe.confirmPayment(...args),
      confirmCardPayment: (...args: unknown[]) =>
        (globalThis as any).__hu07Stripe.confirmCardPayment(...args),
      createPaymentMethod: (...args: unknown[]) =>
        (globalThis as any).__hu07Stripe.createPaymentMethod(...args),
    }),
  }),
  { virtual: true },
);

vi.mock(
  '@stripe/react-stripe-js',
  () => ({
    Elements: ({ children }: any) => children,
    CardElement: () => 'card-element-mock',
    PaymentElement: () => 'payment-element-mock',
    useStripe: () => (globalThis as any).__hu07Stripe,
    useElements: () => ({ getElement: () => ({}) }),
  }),
  { virtual: true },
);

let Checkout: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  (globalThis as any).__hu07Harness = { mode: 'ok', pollState: 'confirmado' };

  const stripeResult = () => {
    const mode = harness().mode;
    if (mode === 'ok') {
      return Promise.resolve({ paymentIntent: { id: 'pi_test', status: 'succeeded' } });
    }
    return Promise.resolve({
      error: {
        code: 'card_declined',
        decline_code: mode === 'insufficient' ? 'insufficient_funds' : 'generic_decline',
        message: mode === 'insufficient' ? MSG_INSUFFICIENT : MSG_OTHER,
      },
    });
  };
  (globalThis as any).__hu07Stripe = {
    confirmPayment: vi.fn(stripeResult),
    confirmCardPayment: vi.fn(stripeResult),
    createPaymentMethod: vi.fn(async () => ({ paymentMethod: { id: 'pm_test' } })),
  };

  importError = null;
  Checkout = null;
  try {
    const checkoutPath = '../src/pages/' + 'Checkout';
    const mod = await import(/* @vite-ignore */ checkoutPath);
    Checkout = (mod as any).default ?? (mod as any).Checkout ?? null;
  } catch (error) {
    importError = error;
  }
});

afterEach(() => vi.unstubAllGlobals());

function assertLoaded() {
  expect(importError, `Pantalla /checkout no implementada: ${importError}`).toBeNull();
  expect(Checkout).not.toBeNull();
}

function cartItemResponse() {
  return {
    producto_id: 1,
    nombre: 'Ibuprofeno 400mg',
    imagen_url: null,
    cantidad: 2,
    precio_regular: 12,
    descuento_porcentaje: 0,
    precio_final: 12,
    subtotal: 24,
    ahorro: 0,
    stock_disponible: 8,
  };
}

function mockCheckoutFetch() {
  let polls = 0;
  const ok = (body: unknown) =>
    Promise.resolve({ ok: true, status: 200, json: async () => body });
  const confirmed = {
    estado: 'confirmado',
    pedido: { numero: ORDER_NUMBER, estado: 'Registrado', monto: 24, moneda: 'PEN' },
  };
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();
    if (url.includes('/api/v1/carrito/items')) return ok({ ...cartItemResponse(), items: [] });
    if (url.includes('/api/v1/carrito')) {
      return ok({
        items_oferta: [],
        items_regulares: [cartItemResponse()],
        subtotal: 24,
        ahorro_total: 0,
        total: 24,
        reserva_expira_en: null,
      });
    }
    if (url.includes('/api/v1/zonas')) {
      return ok([{ id: 1, nombre: 'Lima', distrito: 'Miraflores', tiempo_estimado_min: 30 }]);
    }
    if (url.includes('/api/v1/direcciones')) {
      return ok([
        {
          id: 10,
          direccion_linea1: 'Av. Real 123',
          referencia: null,
          telefono_contacto: '999888777',
          zona_id: 1,
        },
      ]);
    }
    if (url.includes('/api/v1/checkout') && method === 'POST') {
      return ok({
        payment_intent_id: 'pi_test',
        client_secret: 'pi_test_secret',
        monto: 24,
        moneda: 'PEN',
        reserva_expira_en: new Date(Date.now() + 3600_000).toISOString(),
      });
    }
    if (url.includes('/api/v1/pagos/')) {
      polls += 1;
      if (polls === 1) return ok({ estado: 'procesando', pedido: null });
      return ok(harness().pollState === 'confirmado' ? confirmed : { estado: 'rechazado', pedido: null });
    }
    return ok({});
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderCheckout() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/checkout']}>
        <Routes>
          <Route path="/checkout" element={<Checkout />} />
          <Route path="*" element={<Checkout />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('HU-07 /checkout — pago con Stripe Elements', () => {
  it('muestra la captura de entrega y el botón Pagar ahora', async () => {
    assertLoaded();
    mockCheckoutFetch();
    renderCheckout();
    const payButton = await screen.findByRole('button', { name: /Pagar ahora/i });
    expect(payButton).not.toBeNull();
    expect(screen.getByText(/entrega|zona|dirección|direccion|retiro|delivery/i)).not.toBeNull();
    expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull();
  });

  it('pago exitoso: Procesando pago... y confirmación con número BL y monto', async () => {
    assertLoaded();
    harness().mode = 'ok';
    harness().pollState = 'confirmado';
    mockCheckoutFetch();
    renderCheckout();
    fireEvent.click(await screen.findByRole('button', { name: /Pagar ahora/i }));
    await waitFor(
      () => expect(screen.getByText(/Procesando pago\.\.\./)).not.toBeNull(),
      { timeout: 4000 },
    );
    await waitFor(() => expect(screen.getByText(new RegExp(`#${ORDER_NUMBER}`))).not.toBeNull(), {
      timeout: 5000,
    });
    expect(screen.getByText(/S\/\s*24\.00/)).not.toBeNull();
  });

  it('rechazo por fondos insuficientes: mensaje exacto y carrito intacto', async () => {
    assertLoaded();
    harness().mode = 'insufficient';
    harness().pollState = 'rechazado';
    const fetchMock = mockCheckoutFetch();
    renderCheckout();
    fireEvent.click(await screen.findByRole('button', { name: /Pagar ahora/i }));
    await waitFor(() => expect(screen.getByText(MSG_INSUFFICIENT)).not.toBeNull(), {
      timeout: 5000,
    });
    expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull();
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/carrito')),
    ).toBe(true);
  });

  it('rechazo por otra causa: mensaje exacto y permanece en checkout', async () => {
    assertLoaded();
    harness().mode = 'other';
    harness().pollState = 'rechazado';
    mockCheckoutFetch();
    renderCheckout();
    fireEvent.click(await screen.findByRole('button', { name: /Pagar ahora/i }));
    await waitFor(() => expect(screen.getByText(MSG_OTHER)).not.toBeNull(), { timeout: 5000 });
    expect(screen.getByRole('button', { name: /Pagar ahora/i })).not.toBeNull();
    expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull();
  });
});
