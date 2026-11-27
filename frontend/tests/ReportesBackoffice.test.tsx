import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const VENTAS_FIXTURE = {
  fecha_inicio: '2026-10-01',
  fecha_fin: '2026-10-31',
  total_ordenes: 12,
  unidades_vendidas: 34,
  monto_total_facturado: 456.7,
  moneda: 'PEN',
};

const BALANCE_FIXTURE = {
  balance: {
    Registrado: 3,
    'Preparando producto': 2,
    'En camino': 4,
    Entregado: 3,
  },
  total_pedidos: 12,
};

const CRITICO_FIXTURE = {
  stock_bajo: [
    { producto_id: 55, nombre: 'Amoxicilina 500mg', stock_disponible: 3 },
    { producto_id: 58, nombre: 'Loratadina 10mg', stock_disponible: 5 },
  ],
  quiebres: [
    { producto_id: 56, nombre: 'Omeprazol 20mg', stock_disponible: 0 },
  ],
  mayor_rotacion: [
    { producto_id: 57, nombre: 'Ibuprofeno 400mg', unidades_vendidas: 9 },
  ],
};

let Module: React.ComponentType<any> | null = null;
let importError: unknown = null;

async function loadModule(candidates: Array<{ path: string; names: string[] }>) {
  for (const candidate of candidates) {
    try {
      const mod = await import(/* @vite-ignore */ candidate.path);
      for (const name of candidate.names) {
        if (mod[name]) return mod[name] as React.ComponentType<any>;
      }
      const exported = Object.values(mod).find(
        (value) => typeof value === 'function',
      ) as React.ComponentType<any> | undefined;
      if (exported) return exported;
    } catch {
      // Se prueba el siguiente candidato.
    }
  }
  return null;
}

function reportesCandidates() {
  return [
    { path: '../src/pages/' + 'BackofficeReportes', names: ['default', 'BackofficeReportes'] },
    { path: '../src/pages/' + 'ReportesBackoffice', names: ['default', 'ReportesBackoffice'] },
    { path: '../src/pages/' + 'Reportes', names: ['default', 'Reportes'] },
  ];
}

async function setSession() {
  const token = 'token-admin-hu11';
  localStorage.setItem('access_token', token);
  try {
    const store = await import(/* @vite-ignore */ '../src/store/' + 'useAuthStore');
    store.useAuthStore
      ?.getState?.()
      ?.setSession?.(token, { id: 1, email: 'admin@ejemplo.com', rol: 'admin' });
  } catch {
    // La pantalla puede autenticarse solo con el token de localStorage.
  }
}

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
  Module = null;
  importError = null;
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

function assertLoaded(pantalla: string) {
  expect(importError, `Pantalla ${pantalla} no implementada: ${importError}`).toBeNull();
  expect(Module).not.toBeNull();
}

function ok(body: unknown, status = 200) {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return Promise.resolve({
    ok: status < 400,
    status,
    json: async () => body,
    text: async () => text,
    headers: { get: () => 'application/json' },
  });
}

function mockReportesFetch() {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = String(input);

    if (url.includes('/api/v1/backoffice/reportes/ventas')) {
      const inicio = url.match(/[?&]fecha_inicio=([^&]*)/)?.[1];
      const fin = url.match(/[?&]fecha_fin=([^&]*)/)?.[1];
      return ok({
        ...VENTAS_FIXTURE,
        fecha_inicio: inicio ? decodeURIComponent(inicio) : VENTAS_FIXTURE.fecha_inicio,
        fecha_fin: fin ? decodeURIComponent(fin) : VENTAS_FIXTURE.fecha_fin,
      });
    }
    if (url.includes('/api/v1/backoffice/reportes/pedidos-balance')) {
      return ok(BALANCE_FIXTURE);
    }
    if (url.includes('/api/v1/backoffice/reportes/inventario-critico')) {
      return ok(CRITICO_FIXTURE);
    }
    if (url.includes('/api/v1/auth/me')) {
      return ok({ id: 1, email: 'admin@ejemplo.com', rol: 'admin' });
    }
    return ok({});
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderAt(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/backoffice/reportes" element={<Module />} />
          <Route path="*" element={<Module />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function texto(): string {
  return document.body.textContent ?? '';
}

function campo(nombre: string): HTMLElement | null {
  return document.querySelector(`#${nombre}, [name="${nombre}"]`) as HTMLElement | null;
}

async function montarReportes() {
  await setSession();
  Module = await loadModule(reportesCandidates());
  if (!Module)
    importError = new Error('Ninguna pantalla de /backoffice/reportes existe todavía');
  assertLoaded('/backoffice/reportes');
  const fetchMock = mockReportesFetch();
  renderAt('/backoffice/reportes');
  return fetchMock;
}

describe('HU-11 /backoffice/reportes — totales de ventas y rango de fechas', () => {
  it('muestra el selector de rango y los totales de ventas', async () => {
    await montarReportes();

    const inicio = campo('fecha_inicio');
    const fin = campo('fecha_fin');
    const fechas = document.querySelectorAll('input[type="date"]');
    expect(
      (inicio && fin) || fechas.length >= 2,
      'Debe existir el selector de rango (fecha_inicio/fecha_fin)',
    ).toBeTruthy();

    await waitFor(() => {
      const t = texto();
      expect(t).toContain(String(VENTAS_FIXTURE.total_ordenes));
      expect(t).toContain(String(VENTAS_FIXTURE.unidades_vendidas));
      expect(t).toMatch(/456[.,]7/);
    });
  });

  it('consulta el reporte con el rango de fechas elegido', async () => {
    const fetchMock = await montarReportes();
    await waitFor(() => expect(texto()).toMatch(/456[.,]7/));

    const inicio = campo('fecha_inicio');
    const fin = campo('fecha_fin');
    expect(inicio, 'Falta el input fecha_inicio').not.toBeNull();
    expect(fin, 'Falta el input fecha_fin').not.toBeNull();
    fireEvent.change(inicio!, { target: { value: '2026-10-01' } });
    fireEvent.change(fin!, { target: { value: '2026-10-31' } });

    const aplicar = screen.queryAllByRole('button', {
      name: /aplicar|filtrar|consultar|actualizar|buscar|generar/i,
    })[0];
    if (aplicar) {
      fireEvent.click(aplicar);
    } else {
      const form = inicio!.closest('form');
      if (form) fireEvent.submit(form);
    }

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) => {
          const u = String(url);
          return (
            u.includes('/reportes/ventas') &&
            u.includes('fecha_inicio=2026-10-01') &&
            u.includes('fecha_fin=2026-10-31')
          );
        }),
      ).toBe(true),
    );
  });
});

describe('HU-11 /backoffice/reportes — balance de pedidos', () => {
  it('muestra los 4 estados del ciclo de vida', async () => {
    await montarReportes();

    await waitFor(() => {
      const t = texto();
      expect(t).toMatch(/Registrado/i);
      expect(t).toMatch(/Preparando producto/i);
      expect(t).toMatch(/En camino/i);
      expect(t).toMatch(/Entregado/i);
    });
  });
});

describe('HU-11 /backoffice/reportes — inventario crítico', () => {
  it('muestra las tablas de stock bajo, quiebres y rotación', async () => {
    await montarReportes();

    await waitFor(() => {
      expect(screen.queryAllByText(CRITICO_FIXTURE.stock_bajo[0].nombre).length).toBeGreaterThan(0);
      expect(screen.queryAllByText(CRITICO_FIXTURE.quiebres[0].nombre).length).toBeGreaterThan(0);
      expect(
        screen.queryAllByText(CRITICO_FIXTURE.mayor_rotacion[0].nombre).length,
      ).toBeGreaterThan(0);
    });

    const t = texto();
    expect(t).toMatch(/stock bajo/i);
    expect(t).toMatch(/quiebre/i);
    expect(t).toMatch(/rotaci[oó]n/i);
    expect(t).toContain(String(CRITICO_FIXTURE.stock_bajo[0].stock_disponible));
    expect(t).toContain(String(CRITICO_FIXTURE.mayor_rotacion[0].unidades_vendidas));
  });
});
