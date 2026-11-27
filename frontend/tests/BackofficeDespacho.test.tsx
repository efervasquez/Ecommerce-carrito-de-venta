import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const ZONA_ID = 1;
const NUMERO_1 = 'BL-10045';
const NUMERO_2 = 'BL-10046';

type Harness = {
  pedidos: Array<Record<string, unknown>>;
  zonas: Array<Record<string, unknown>>;
  motorizados: Array<{ id: number; email: string; rol: string }>;
  asignaciones: Array<Record<string, unknown>>;
  assignmentStatus: number;
};

function harness(): Harness {
  return (globalThis as any).__hu08BackofficeHarness as Harness;
}

let Backoffice: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  localStorage.setItem('access_token', 'token-admin-hu08');

  (globalThis as any).__hu08BackofficeHarness = {
    pedidos: [
      {
        numero: NUMERO_1,
        estado: 'Registrado',
        zona_id: ZONA_ID,
        distrito: 'Centro',
        metodo_entrega: 'delivery',
        motorizado_id: null,
        monto: 24,
        creado_en: '2026-11-27T01:00:00',
      },
      {
        numero: NUMERO_2,
        estado: 'Registrado',
        zona_id: ZONA_ID,
        distrito: 'Centro',
        metodo_entrega: 'delivery',
        motorizado_id: null,
        monto: 12,
        creado_en: '2026-11-27T01:01:00',
      },
    ],
    zonas: [
      {
        zona_id: ZONA_ID,
        nombre: 'Botica Centro',
        distrito: 'Centro',
        pedidos_registrados: 2,
        pedidos_preparando: 0,
        pedidos_en_camino: 0,
        pedidos_entregados: 0,
      },
    ],
    motorizados: [{ id: 7, email: 'motorizado@ejemplo.com', rol: 'motorizado' }],
    asignaciones: [],
    assignmentStatus: 200,
  } satisfies Harness;

  try {
    const store = await import(/* @vite-ignore */ '../src/store/' + 'useAuthStore');
    store.useAuthStore
      ?.getState?.()
      ?.setSession?.('token-admin-hu08', { id: 1, email: 'admin@ejemplo.com', rol: 'admin' });
  } catch {
    // La pantalla puede autenticarse solo con el token de localStorage.
  }

  importError = null;
  Backoffice = null;
  const candidates = [
    { path: '../src/pages/' + 'BackofficeDespacho', names: ['default', 'BackofficeDespacho'] },
    { path: '../src/pages/' + 'DespachoBackoffice', names: ['default', 'DespachoBackoffice'] },
    { path: '../src/pages/' + 'Backoffice', names: ['default', 'Backoffice'] },
  ];
  for (const candidate of candidates) {
    try {
      const mod = await import(/* @vite-ignore */ candidate.path);
      for (const name of candidate.names) {
        if (mod[name]) {
          Backoffice = mod[name];
          break;
        }
      }
    } catch {
      // Se prueba la siguiente pantalla candidata.
    }
    if (Backoffice) break;
  }
  if (!Backoffice) {
    importError = new Error('Ninguna pantalla de /backoffice/despacho existe todavía');
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

function assertLoaded() {
  expect(importError, `Pantalla /backoffice/despacho no implementada: ${importError}`).toBeNull();
  expect(Backoffice).not.toBeNull();
}

function ok(body: unknown, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: async () => body });
}

function mockDespachoFetch() {
  const h = harness();
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : {};

    if (url.includes('/api/v1/despacho/asignaciones') && method === 'POST') {
      h.asignaciones.push(body);
      return ok({ asignados: body.pedido_numeros ?? [] }, h.assignmentStatus);
    }
    if (url.includes('/api/v1/despacho/zonas')) {
      return ok(h.zonas);
    }
    if (url.includes('/api/v1/despacho/motorizados')) {
      return ok(h.motorizados);
    }
    if (url.includes('/api/v1/despacho/pedidos')) {
      let pedidos = [...h.pedidos];
      if (body.estado) pedidos = pedidos.filter((p) => p.estado === body.estado);
      if (url.includes('estado=')) {
        const estado = decodeURIComponent(url.split('estado=')[1].split('&')[0]);
        pedidos = pedidos.filter((p) => p.estado === estado);
      }
      if (url.includes('zona_id=')) {
        const zona = Number(url.split('zona_id=')[1].split('&')[0]);
        pedidos = pedidos.filter((p) => p.zona_id === zona);
      }
      return ok(pedidos);
    }
    if (url.includes('/api/v1/zonas')) return ok(h.zonas);
    if (url.includes('/api/v1/auth/me')) {
      return ok({ id: 1, email: 'admin@ejemplo.com', rol: 'admin' });
    }
    return ok({});
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderBackoffice() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/backoffice/despacho']}>
        <Routes>
          <Route path="/backoffice/despacho" element={<Backoffice />} />
          <Route path="*" element={<Backoffice />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('HU-08 /backoffice/despacho — buzón y asignación', () => {
  it('muestra el buzón agrupado por zona con los pedidos registrados', async () => {
    assertLoaded();
    mockDespachoFetch();
    renderBackoffice();
    expect((await screen.findAllByText(NUMERO_1)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(NUMERO_2).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Centro/i).length).toBeGreaterThan(0);
  });

  it('muestra los conteos por zona devueltos por el buzón', async () => {
    assertLoaded();
    mockDespachoFetch();
    renderBackoffice();
    await screen.findAllByText(NUMERO_1);
    expect(screen.getAllByText(/Registrados/i).length).toBeGreaterThan(0);
  });

  it('filtra el buzón por estado', async () => {
    assertLoaded();
    const fetchMock = mockDespachoFetch();
    renderBackoffice();
    await screen.findAllByText(NUMERO_1);
    const estadoSelect = document.querySelector('#estado') as HTMLSelectElement | null;
    expect(estadoSelect).not.toBeNull();
    fireEvent.change(estadoSelect!, { target: { value: 'Registrado' } });
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) => String(url).includes('estado=Registrado')),
      ).toBe(true),
    );
  });

  it('asigna el lote seleccionado al motorizado', async () => {
    assertLoaded();
    const fetchMock = mockDespachoFetch();
    renderBackoffice();
    await screen.findAllByRole('checkbox');
    const checks = screen.getAllByRole('checkbox');
    fireEvent.click(checks[0]);
    if (checks[1]) fireEvent.click(checks[1]);

    const motorizadoInput = document.querySelector('#motorizado') as HTMLInputElement | null;
    expect(motorizadoInput).not.toBeNull();
    fireEvent.change(motorizadoInput!, { target: { value: '7' } });

    const assignButton = await screen.findByRole('button', { name: /asignar/i });
    fireEvent.click(assignButton);

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).includes('/api/v1/despacho/asignaciones') &&
          (init?.method ?? 'GET').toUpperCase() === 'POST',
      );
      expect(call, 'Debe llamar a POST /despacho/asignaciones').toBeTruthy();
      const payload = JSON.parse(String(call![1]!.body));
      expect(payload.zona_id).toBe(ZONA_ID);
      expect(payload.motorizado_id).toBe(7);
      expect(Array.isArray(payload.pedido_numeros)).toBe(true);
      expect(payload.pedido_numeros.length).toBeGreaterThan(0);
    });
  });
});
