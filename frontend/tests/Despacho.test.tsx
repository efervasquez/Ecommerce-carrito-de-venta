import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const ZONA_ID = 1;
const NUMERO_1 = 'BL-10045';
const NUMERO_2 = 'BL-10046';
const INVALID_TRANSITION =
  "Transición de estado inválida: el pedido debe pasar primero por 'Preparando producto' y 'En camino'";

type Harness = {
  pendientes: Array<Record<string, unknown>>;
  patchStatus: number;
  patchDetail: string;
};

function harness(): Harness {
  return (globalThis as any).__hu08DespachoHarness as Harness;
}

let Despacho: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  localStorage.setItem('access_token', 'token-motorizado-hu08');

  (globalThis as any).__hu08DespachoHarness = {
    pendientes: [
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
    patchStatus: 200,
    patchDetail: '',
  } satisfies Harness;

  try {
    const store = await import(/* @vite-ignore */ '../src/store/' + 'useAuthStore');
    store.useAuthStore
      ?.getState?.()
      ?.setSession?.('token-motorizado-hu08', {
        id: 7,
        email: 'motorizado@ejemplo.com',
        rol: 'motorizado',
      });
  } catch {
    // La pantalla puede autenticarse solo con el token de localStorage.
  }

  importError = null;
  Despacho = null;
  const candidates = [
    { path: '../src/pages/' + 'Despacho', names: ['default', 'Despacho'] },
    { path: '../src/pages/' + 'DespachoMotorizado', names: ['default', 'DespachoMotorizado'] },
  ];
  for (const candidate of candidates) {
    try {
      const mod = await import(/* @vite-ignore */ candidate.path);
      for (const name of candidate.names) {
        if (mod[name]) {
          Despacho = mod[name];
          break;
        }
      }
    } catch {
      // Se prueba la siguiente pantalla candidata.
    }
    if (Despacho) break;
  }
  if (!Despacho) {
    importError = new Error('Ninguna pantalla de /despacho existe todavía');
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

function assertLoaded() {
  expect(importError, `Pantalla /despacho no implementada: ${importError}`).toBeNull();
  expect(Despacho).not.toBeNull();
}

function ok(body: unknown, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: async () => body });
}

function pedido(numero: string, estado: string) {
  return {
    numero,
    estado,
    zona_id: ZONA_ID,
    distrito: 'Centro',
    metodo_entrega: 'delivery',
    motorizado_id: 7,
    monto: 24,
    creado_en: '2026-11-27T01:00:00',
  };
}

function mockDespachoFetch() {
  const h = harness();
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : {};

    if (url.includes('/api/v1/despacho/') && method === 'PATCH') {
      const match = url.match(/\/pedidos\/([^/]+)\/estado/);
      const numero = match?.[1] ?? NUMERO_1;
      if (h.patchStatus >= 400) {
        return ok({ detail: h.patchDetail }, h.patchStatus);
      }
      h.pendientes = h.pendientes.map((p) =>
        p.numero === numero ? pedido(numero, body.estado) : p,
      );
      return ok(pedido(numero, body.estado));
    }
    if (url.includes('/api/v1/despacho/pedidos/pendientes')) {
      return ok(h.pendientes);
    }
    if (url.includes('/api/v1/despacho/pedidos/') && method === 'POST') {
      const match = url.match(/\/pedidos\/([^/]+)\/auto-asignar/);
      const numero = match?.[1] ?? NUMERO_1;
      h.pendientes = h.pendientes.filter((p) => p.numero !== numero);
      return ok(pedido(numero, 'Preparando producto'));
    }
    if (url.includes('/api/v1/despacho/pedidos')) {
      return ok(h.pendientes);
    }
    if (url.includes('/api/v1/zonas')) {
      return ok([{ id: ZONA_ID, nombre: 'Botica Centro', distrito: 'Centro' }]);
    }
    if (url.includes('/api/v1/auth/me')) {
      return ok({ id: 7, email: 'motorizado@ejemplo.com', rol: 'motorizado' });
    }
    return ok({});
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderDespacho() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/despacho']}>
        <Routes>
          <Route path="/despacho" element={<Despacho />} />
          <Route path="*" element={<Despacho />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('HU-08 /despacho — pendientes FIFO y ciclo de vida', () => {
  it('muestra los pendientes de la zona en orden de llegada (FIFO)', async () => {
    assertLoaded();
    mockDespachoFetch();
    renderDespacho();
    expect((await screen.findAllByText(NUMERO_1)).length).toBeGreaterThan(0);
    const numeros = screen
      .getAllByText(/BL-\d+/)
      .map((el) => el.textContent ?? '')
      .filter((texto, index, arr) => arr.indexOf(texto) === index);
    expect(numeros.indexOf(NUMERO_1)).toBeLessThan(numeros.indexOf(NUMERO_2));
  });

  it('auto-asigna el pedido más antiguo por POST auto-asignar', async () => {
    assertLoaded();
    const fetchMock = mockDespachoFetch();
    renderDespacho();
    const buttons = await screen.findAllByRole('button', { name: /auto.?asignar/i });
    fireEvent.click(buttons[0]);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            /\/api\/v1\/despacho\/pedidos\/BL-\d+\/auto-asignar/.test(String(url)) &&
            (init?.method ?? 'GET').toUpperCase() === 'POST',
        ),
      ).toBe(true),
    );
  });

  it('avanza el pedido a En camino y luego a Entregado', async () => {
    assertLoaded();
    harness().pendientes = [
      pedido(NUMERO_1, 'Preparando producto'),
      pedido(NUMERO_2, 'En camino'),
    ];
    const fetchMock = mockDespachoFetch();
    renderDespacho();
    await screen.findAllByText(NUMERO_1);

    fireEvent.click((await screen.findAllByRole('button', { name: /en camino/i }))[0]);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            /\/pedidos\/BL-\d+\/estado/.test(String(url)) &&
            (init?.method ?? 'GET').toUpperCase() === 'PATCH' &&
            JSON.parse(String(init?.body)).estado === 'En camino',
        ),
      ).toBe(true),
    );

    fireEvent.click((await screen.findAllByRole('button', { name: /entregado/i }))[0]);
    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(
          ([url, init]) =>
            /\/pedidos\/BL-\d+\/estado/.test(String(url)) &&
            (init?.method ?? 'GET').toUpperCase() === 'PATCH' &&
            JSON.parse(String(init?.body)).estado === 'Entregado',
        ),
      ).toBe(true),
    );
  });

  it('muestra el mensaje exacto de transición inválida (409)', async () => {
    assertLoaded();
    harness().patchStatus = 409;
    harness().patchDetail = INVALID_TRANSITION;
    harness().pendientes = [
      pedido(NUMERO_1, 'Preparando producto'),
      pedido(NUMERO_2, 'En camino'),
    ];
    mockDespachoFetch();
    renderDespacho();
    await screen.findAllByText(NUMERO_1);
    const buttons =
      screen.queryAllByRole('button', { name: /entregado/i }) ??
      screen.queryAllByRole('button', { name: /en camino/i });
    expect(buttons.length).toBeGreaterThan(0);
    fireEvent.click(buttons[0]);
    await waitFor(() => expect(screen.getByText(INVALID_TRANSITION)).not.toBeNull());
  });
});
