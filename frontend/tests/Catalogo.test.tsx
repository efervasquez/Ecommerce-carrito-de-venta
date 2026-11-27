import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

const product = {
  id: 1,
  nombre: 'Ibuprofeno 400mg',
  componentes: 'Ibuprofeno',
  imagen_url: 'https://example.test/ibuprofeno.jpg',
  precio_regular: 12,
  moneda: 'PEN',
  descuento_porcentaje: 20,
  stock_disponible: 4,
  stock_bajo: true,
  precios_bajos: true,
  requiere_receta: true,
};

const page = (items = [product], next_cursor: string | null = null, has_next = false) => ({
  items,
  next_cursor,
  has_next,
});

let Catalogo: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  Catalogo = null;
  try {
    const mod = await import('../src/pages/Catalogo');
    Catalogo = (mod as any).default ?? (mod as any).Catalogo ?? null;
  } catch (error) {
    importError = error;
  }
});

afterEach(() => vi.unstubAllGlobals());

function renderCatalogo() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/catalogo']}>
        <Catalogo />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function assertLoaded() {
  expect(importError, `Pantalla Catalogo no implementada: ${importError}`).toBeNull();
  expect(Catalogo).not.toBeNull();
}

function mockFetch(response: unknown, ok = true) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status: ok ? 200 : 500,
    json: async () => response,
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function mockVirtualizerMeasurements() {
  class MockResizeObserver {
    private callback: (entries: unknown[]) => void;

    constructor(callback: (entries: unknown[]) => void) {
      this.callback = callback;
    }

    observe(target: Element) {
      this.callback([
        { target, contentRect: { width: 800, height: 600 } },
      ]);
    }

    unobserve() {}

    disconnect() {}
  }

  vi.stubGlobal('ResizeObserver', MockResizeObserver);
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width: 800,
    height: 600,
    top: 0,
    right: 800,
    bottom: 600,
    left: 0,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  } as DOMRect);
  vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600);
  vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(600);
  vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockReturnValue(1200);
}

describe('HU-03 /catalogo — estados y búsqueda', () => {
  it('muestra carga visible mientras consulta el catálogo', () => {
    assertLoaded();
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => undefined)));
    renderCatalogo();
    const loading =
      screen.queryByRole('progressbar') ??
      screen.queryByText(/cargando|loading|buscando/i);
    expect(loading).not.toBeNull();
  });

  it('muestra error visible cuando falla la consulta', async () => {
    assertLoaded();
    mockFetch({}, false);
    renderCatalogo();
    await waitFor(() => expect(screen.queryByText(/error|falló|fallo|intenta/i)).not.toBeNull());
  });

  it('muestra estado visible sin resultados', async () => {
    assertLoaded();
    mockFetch(page([]));
    renderCatalogo();
    await waitFor(() => expect(screen.queryByText(/sin resultados|no se encontraron productos|no encontramos|vacío|vacio/i)).not.toBeNull());
  });

  it('busca usando q y GET /api/v1/catalogo/buscar', async () => {
    assertLoaded();
    const fetchMock = mockFetch(page());
    renderCatalogo();
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'ibuprofno 400' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/catalogo/buscar'))).toBe(true);
    });
    const matchingCall = fetchMock.mock.calls.find(([url]) => String(url).includes('/api/v1/catalogo/buscar'));
    expect(String(matchingCall?.[0])).toContain('q=');
  });
});

describe('HU-03 tarjetas y scroll incremental', () => {
  it('muestra todos los campos de producto y reglas visuales exactas', async () => {
    assertLoaded();
    mockFetch(page());
    mockVirtualizerMeasurements();
    renderCatalogo();
    await waitFor(() => expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull());
    expect(screen.getByText('Ibuprofeno')).not.toBeNull();
    expect(screen.getByText(/12/)).not.toBeNull();
    expect(screen.getByText(/20%/)).not.toBeNull();
    expect(screen.getByText('Últimas unidades disponibles (menos de 6 en stock)')).not.toBeNull();
    expect(screen.getByText('Precios bajos')).not.toBeNull();
    expect(screen.getByText(/requiere receta|receta/i)).not.toBeNull();
    expect(screen.getByText('Agregar al carrito').closest('button')).not.toBeNull();
    expect(screen.queryByText(/Página 1|Página 2|Siguiente|Anterior/i)).toBeNull();
  });

  it('solicita la siguiente tanda con next_cursor y conserva la primera', async () => {
    assertLoaded();
    const secondProduct = { ...product, id: 2, nombre: 'Paracetamol 500mg' };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => page([product], 'cursor-2', true) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => page([secondProduct]) });
    vi.stubGlobal('fetch', fetchMock);
    mockVirtualizerMeasurements();
    renderCatalogo();
    await waitFor(() => expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull());
    const catalogContainer = screen.getByLabelText('Productos del catálogo');
    Object.defineProperty(catalogContainer, 'scrollHeight', { configurable: true, value: 1200 });
    Object.defineProperty(catalogContainer, 'clientHeight', { configurable: true, value: 600 });
    Object.defineProperty(catalogContainer, 'scrollTop', { configurable: true, value: 800 });
    fireEvent.scroll(catalogContainer);
    await waitFor(() => expect(screen.getByText('Paracetamol 500mg')).not.toBeNull());
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain('cursor=cursor-2');
    expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull();
  });
});

describe('HU-03 agregar al carrito temporal', () => {
  it('incrementa el contador local y permanece en el catálogo', async () => {
    assertLoaded();
    mockFetch(page());
    mockVirtualizerMeasurements();
    renderCatalogo();
    await waitFor(() => expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull());
    const addButton = screen.getByText('Agregar al carrito').closest('button');
    expect(addButton).not.toBeNull();
    fireEvent.click(addButton as HTMLButtonElement);
    expect(screen.getByText('Ibuprofeno 400mg')).not.toBeNull();
    expect(screen.getByText('Agregar al carrito').closest('button')).not.toBeNull();
    expect(screen.queryByText(/carrito\D*1/i)).not.toBeNull();
  });
});
