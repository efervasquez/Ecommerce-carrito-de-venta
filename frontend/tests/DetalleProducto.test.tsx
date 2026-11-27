import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const detailProduct = {
  id: 1,
  nombre: 'Azitromicina 500mg',
  imagen_url: 'https://example.test/azitromicina.jpg',
  componentes: 'Azitromicina dihidrato 500mg',
  precio_regular: 18.5,
  moneda: 'PEN',
  descuento_porcentaje: 10,
  requiere_receta: true,
  detalle: 'Antibiótico de amplio espectro.',
  presentacion: 'Caja con 3 tabletas recubiertas',
  metodos_entrega: ['Delivery', 'Retiro en botica'],
  contraindicaciones: 'Hipersensibilidad a macrólidos.',
  precauciones_advertencias: 'Usar bajo supervisión profesional.',
  reacciones_adversas: 'Náuseas y dolor abdominal.',
  precios_bajos: true,
  stock_disponible: 10,
};

let DetalleProducto: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  DetalleProducto = null;
  try {
    const detailModule = await import('../src/pages/DetalleProducto');
    DetalleProducto = (detailModule as any).default ?? (detailModule as any).DetalleProducto ?? null;
  } catch (error) {
    importError = error;
  }
});

afterEach(() => vi.unstubAllGlobals());

function renderDetail(entry = '/catalogo/productos/1') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/catalogo/productos/:id" element={<DetalleProducto />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockDetailFetch(product = detailProduct) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => product,
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

const emptyCartResponse = () => ({
  items_oferta: [],
  items_regulares: [],
  subtotal: 0,
  ahorro_total: 0,
  total: 0,
  reserva_expira_en: null,
});

const cartItemResponse = (producto_id = 1, cantidad = 1) => ({
  producto_id,
  nombre: 'Azitromicina 500mg',
  imagen_url: null,
  cantidad,
  precio_regular: 18.5,
  descuento_porcentaje: 10,
  precio_final: 16.65,
  subtotal: 18.5 * cantidad,
  ahorro: 1.85 * cantidad,
  stock_disponible: 10,
});

const cartWith = (items: ReturnType<typeof cartItemResponse>[]) => ({
  items_oferta: items.filter((item) => item.descuento_porcentaje > 0),
  items_regulares: items.filter((item) => item.descuento_porcentaje <= 0),
  subtotal: 0,
  ahorro_total: 0,
  total: 0,
  reserva_expira_en: null,
});

function mockDetailRoutedFetch(options: {
  product?: unknown;
  cart?: unknown;
  addedCart?: unknown;
} = {}) {
  const {
    product = detailProduct,
    cart = emptyCartResponse(),
    addedCart = cartWith([cartItemResponse(1, 2)]),
  } = options;
  const ok = (body: unknown) =>
    Promise.resolve({ ok: true, status: 200, json: async () => body });
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/api/v1/carrito/items')) return ok(addedCart);
    if (url.includes('/api/v1/carrito')) return ok(cart);
    if (url.includes('/api/v1/catalogo/productos')) return ok(product);
    return Promise.resolve({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'not found' }),
    });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function assertLoaded() {
  expect(importError, `Pantalla HU-04 no implementada: ${importError}`).toBeNull();
  expect(DetalleProducto).not.toBeNull();
}

describe('HU-04 /catalogo/productos/{id} — detalle comercial y clínico', () => {
  it('consulta el detalle por id y muestra todos los bloques obligatorios', async () => {
    assertLoaded();
    const fetchMock = mockDetailRoutedFetch();
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());

    const detailCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes('/api/v1/catalogo/productos/1'),
    );
    expect(detailCall).toBeDefined();
    expect(screen.getByText('Azitromicina dihidrato 500mg')).not.toBeNull();
    expect(screen.getByText(/18\.50|18,50/)).not.toBeNull();
    expect(screen.getByText(/10%/)).not.toBeNull();
    expect(screen.getByText('Necesita receta para la venta')).not.toBeNull();
    expect(screen.getByText('Antibiótico de amplio espectro.')).not.toBeNull();
    expect(screen.getByText('Caja con 3 tabletas recubiertas')).not.toBeNull();
    expect(screen.getByText(/Delivery, Retiro en botica/)).not.toBeNull();
    expect(screen.getByText('Contraindicaciones')).not.toBeNull();
    expect(screen.getByText('Hipersensibilidad a macrólidos.')).not.toBeNull();
    expect(screen.getByText('Precauciones/Advertencias')).not.toBeNull();
    expect(screen.getByText('Usar bajo supervisión profesional.')).not.toBeNull();
    expect(screen.getByText('Reacciones adversas')).not.toBeNull();
    expect(screen.getByText('Náuseas y dolor abdominal.')).not.toBeNull();
    expect(screen.getByText('Precios bajos')).not.toBeNull();
  });

  it('muestra producto de venta libre cuando no requiere receta', async () => {
    assertLoaded();
    mockDetailRoutedFetch({ product: { ...detailProduct, requiere_receta: false } });
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    expect(screen.getByText('Producto de venta libre')).not.toBeNull();
  });
});

describe('HU-04 navegación y acción temporal', () => {
  it('mantiene la ruta de detalle y muestra cantidad y botón de compra', async () => {
    assertLoaded();
    mockDetailRoutedFetch();
    renderDetail('/catalogo/productos/1');
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    expect(screen.getByRole('spinbutton')).not.toBeNull();
    expect(screen.getByText('Agregar al carrito').closest('button')).not.toBeNull();
  });

  it('cantidad válida conserva la ficha, confirma el agregado y actualiza Ver carrito (N)', async () => {
    assertLoaded();
    const fetchMock = mockDetailRoutedFetch();
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    const quantity = screen.getByRole('spinbutton') as HTMLInputElement;
    fireEvent.change(quantity, { target: { value: '2' } });
    fireEvent.click(screen.getByText('Agregar al carrito').closest('button') as HTMLButtonElement);
    await waitFor(() => expect(screen.getByText('Producto agregado al carrito.')).not.toBeNull());
    expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull();
    expect(screen.getByText(/Ver carrito \(\s*2\s*\)/)).not.toBeNull();
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/carrito/items')),
    ).toBe(true);
  });

  it('cantidad mayor al stock muestra error y no ejecuta la petición de agregado', async () => {
    assertLoaded();
    const fetchMock = mockDetailRoutedFetch({
      product: { ...detailProduct, stock_disponible: 3 },
    });
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '4' } });
    fireEvent.click(screen.getByText('Agregar al carrito').closest('button') as HTMLButtonElement);
    expect(screen.queryByRole('alert') ?? screen.queryByText(/stock|disponible|cantidad|máximo|maximo/i)).not.toBeNull();
    // GET /carrito + GET /catalogo/productos/{id}; no se dispara el POST de agregado.
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/carrito/items')),
    ).toBe(false);
  });

  it('producto sin stock deshabilita Agregar al carrito', async () => {
    assertLoaded();
    mockDetailRoutedFetch({ product: { ...detailProduct, stock_disponible: 0 } });
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    const addButton = screen.getByText('Agregar al carrito').closest('button') as HTMLButtonElement;
    expect(addButton.disabled).toBe(true);
  });
});
