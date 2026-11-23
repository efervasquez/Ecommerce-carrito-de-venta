import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

const cartPayload = {
  items_oferta: [
    {
      producto_id: 1,
      nombre: 'Ibuprofeno 400mg',
      cantidad: 2,
      precio_regular: 12,
      descuento_porcentaje: 20,
      precio_final: 9.6,
      subtotal: 19.2,
      ahorro: 4.8,
    },
  ],
  items_regulares: [
    {
      producto_id: 2,
      nombre: 'Paracetamol 500mg',
      cantidad: 1,
      precio_regular: 8,
      descuento_porcentaje: 0,
      precio_final: 8,
      subtotal: 8,
      ahorro: 0,
    },
  ],
  subtotal: 32,
  ahorro_total: 4.8,
  total: 27.2,
  reserva_expira_en: '2026-11-24T12:00:00Z',
};

let Carrito: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  Carrito = null;
  try {
    const mod = await import('../src/pages/Carrito');
    Carrito = (mod as any).default ?? (mod as any).Carrito ?? null;
  } catch (error) {
    importError = error;
  }
});

afterEach(() => vi.unstubAllGlobals());

function renderCarrito() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/carrito']}>
        <Carrito />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function assertLoaded() {
  expect(importError, `Pantalla Carrito no implementada: ${importError}`).toBeNull();
  expect(Carrito).not.toBeNull();
}

function mockCartFetch(payload = cartPayload) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => payload,
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('HU-05 /carrito — ofertas, cantidades y totales', () => {
  it('muestra ofertas primero y productos regulares después', async () => {
    assertLoaded();
    mockCartFetch();
    renderCarrito();
    await waitFor(() => expect(screen.getByText('Productos en Oferta')).not.toBeNull());
    expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull();
    expect(screen.getByText('Paracetamol 500mg')).not.toBeNull();
    expect(screen.getByText('20% DSCTO')).not.toBeNull();
    expect(screen.getByText(/27\.20|27,20/)).not.toBeNull();
    expect(screen.getByText(/4\.80|4,80/)).not.toBeNull();
    expect(screen.getByText(/32\.00|32,00/)).not.toBeNull();
  });

  it('permite cambiar cantidad y eliminar sin abandonar la pantalla', async () => {
    assertLoaded();
    const fetchMock = mockCartFetch();
    renderCarrito();
    await waitFor(() => expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull());

    const quantity = screen.getAllByRole('spinbutton')[0] as HTMLInputElement;
    fireEvent.change(quantity, { target: { value: '3' } });
    fireEvent.blur(quantity);
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/carrito/items/1'))).toBe(true);
    });

    const remove = screen.getByRole('button', { name: /eliminar.*Ibuprofeno|eliminar/i });
    fireEvent.click(remove);
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/carrito/items/1'))).toBe(true));
    expect(screen.getByText('Productos en Oferta')).not.toBeNull();
  });

  it('muestra estado de expiración de reserva cuando existe', async () => {
    assertLoaded();
    mockCartFetch();
    renderCarrito();
    await waitFor(() => expect(screen.getByText(/reserva|expira/i)).not.toBeNull());
  });
});

describe('HU-05 carrito vacío y errores', () => {
  it('muestra estado vacío con totales cero', async () => {
    assertLoaded();
    mockCartFetch({
      items_oferta: [],
      items_regulares: [],
      subtotal: 0,
      ahorro_total: 0,
      total: 0,
      reserva_expira_en: null,
    });
    renderCarrito();
    await waitFor(() => expect(screen.queryByText(/carrito vacío|carrito vacio|sin productos|vacío|vacio/i)).not.toBeNull());
  });

  it('muestra error visible si falla la lectura del carrito', async () => {
    assertLoaded();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }));
    renderCarrito();
    await waitFor(() => expect(screen.queryByText(/error|intenta|falló|fallo/i)).not.toBeNull());
  });
});
