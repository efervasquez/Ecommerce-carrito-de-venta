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

function assertLoaded() {
  expect(importError, `Pantalla HU-04 no implementada: ${importError}`).toBeNull();
  expect(DetalleProducto).not.toBeNull();
}

describe('HU-04 /catalogo/productos/{id} — detalle comercial y clínico', () => {
  it('consulta el detalle por id y muestra todos los bloques obligatorios', async () => {
    assertLoaded();
    const fetchMock = mockDetailFetch();
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());

    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/api/v1/catalogo/productos/1');
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
    mockDetailFetch({ ...detailProduct, requiere_receta: false });
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    expect(screen.getByText('Producto de venta libre')).not.toBeNull();
  });
});

describe('HU-04 navegación y acción temporal', () => {
  it('mantiene la ruta de detalle y muestra cantidad y botón de compra', async () => {
    assertLoaded();
    mockDetailFetch();
    renderDetail('/catalogo/productos/1');
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    expect(screen.getByRole('spinbutton')).not.toBeNull();
    expect(screen.getByText('Agregar al carrito').closest('button')).not.toBeNull();
  });

  it('cantidad válida conserva la ficha y actualiza el contador local/temporal', async () => {
    assertLoaded();
    mockDetailFetch();
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    const quantity = screen.getByRole('spinbutton') as HTMLInputElement;
    fireEvent.change(quantity, { target: { value: '2' } });
    fireEvent.click(screen.getByText('Agregar al carrito').closest('button') as HTMLButtonElement);
    expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull();
    expect(screen.queryByText(/carrito\D*2/i) ?? screen.queryByText(/carrito\D*1/i)).not.toBeNull();
  });

  it('cantidad mayor al stock muestra error y no ejecuta una segunda petición', async () => {
    assertLoaded();
    const fetchMock = mockDetailFetch({ ...detailProduct, stock_disponible: 3 });
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '4' } });
    fireEvent.click(screen.getByText('Agregar al carrito').closest('button') as HTMLButtonElement);
    expect(screen.queryByRole('alert') ?? screen.queryByText(/stock|disponible|cantidad|máximo|maximo/i)).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('producto sin stock deshabilita Agregar al carrito', async () => {
    assertLoaded();
    mockDetailFetch({ ...detailProduct, stock_disponible: 0 });
    renderDetail();
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Azitromicina 500mg' })).not.toBeNull());
    const addButton = screen.getByText('Agregar al carrito').closest('button') as HTMLButtonElement;
    expect(addButton.disabled).toBe(true);
  });
});
