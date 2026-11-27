import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const PEDIDO = 'BL-10045';
const RECLAMO_1 = {
  id: 1,
  pedido_origen_numero: PEDIDO,
  pedido_reposicion_numero: 'BL-REP-10045',
  producto_id: 55,
  estado: 'aprobado',
  intentos_adicionales_realizados: 0,
  creado_en: '2026-11-27T01:00:00',
};
const RECLAMO_2 = {
  id: 2,
  pedido_origen_numero: 'BL-10046',
  pedido_reposicion_numero: 'BL-REP-10046',
  producto_id: 56,
  estado: 'escalado_supervision',
  intentos_adicionales_realizados: 3,
  creado_en: '2026-11-27T02:00:00',
};

type Harness = {
  reclamos: Array<Record<string, unknown>>;
  pedido: Record<string, unknown>;
  postStatus: number;
  postDetail: string;
};

function harness(): Harness {
  return (globalThis as any).__hu09ReclamosHarness as Harness;
}

function freshHarness(): Harness {
  return {
    reclamos: [RECLAMO_1, RECLAMO_2],
    pedido: {
      numero: PEDIDO,
      estado: 'Entregado',
      monto: 24,
      moneda: 'PEN',
      metodo_entrega: 'delivery',
      items: [{ producto_id: 55, nombre: 'Paracetamol', cantidad: 1 }],
    },
    postStatus: 201,
    postDetail: '',
  };
}

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

function newClaimCandidates() {
  return [
    { path: '../src/pages/' + 'ReclamoNuevo', names: ['default', 'ReclamoNuevo', 'NuevoReclamo'] },
    { path: '../src/pages/' + 'NuevoReclamo', names: ['default', 'NuevoReclamo', 'ReclamoNuevo'] },
    { path: '../src/pages/' + 'ReclamosNuevo', names: ['default', 'ReclamosNuevo', 'ReclamoNuevo'] },
    { path: '../src/pages/' + 'RegistrarReclamo', names: ['default', 'RegistrarReclamo'] },
    { path: '../src/modules/reclamos/' + 'ReclamoNuevo', names: ['default', 'ReclamoNuevo'] },
    { path: '../src/modules/reclamos/' + 'NuevoReclamo', names: ['default', 'NuevoReclamo'] },
    { path: '../src/modules/reclamos/' + 'RegistrarReclamo', names: ['default', 'RegistrarReclamo'] },
    { path: '../src/modules/reclamos/' + 'ReclamoForm', names: ['default', 'ReclamoForm'] },
  ];
}

function historyCandidates() {
  return [
    { path: '../src/pages/' + 'Reclamos', names: ['default', 'Reclamos', 'MisReclamos'] },
    { path: '../src/pages/' + 'MisReclamos', names: ['default', 'MisReclamos', 'Reclamos'] },
    { path: '../src/pages/' + 'HistorialReclamos', names: ['default', 'HistorialReclamos'] },
    { path: '../src/modules/reclamos/' + 'Reclamos', names: ['default', 'Reclamos', 'MisReclamos'] },
    { path: '../src/modules/reclamos/' + 'MisReclamos', names: ['default', 'MisReclamos', 'Reclamos'] },
    { path: '../src/modules/reclamos/' + 'ListaReclamos', names: ['default', 'ListaReclamos'] },
    { path: '../src/modules/reclamos/' + 'ReclamosList', names: ['default', 'ReclamosList'] },
  ];
}

function backofficeCandidates() {
  return [
    { path: '../src/pages/' + 'BackofficeReclamos', names: ['default', 'BackofficeReclamos'] },
    { path: '../src/pages/' + 'ReclamosBackoffice', names: ['default', 'ReclamosBackoffice'] },
    { path: '../src/pages/' + 'AdminReclamos', names: ['default', 'AdminReclamos'] },
    { path: '../src/modules/reclamos/' + 'BackofficeReclamos', names: ['default', 'BackofficeReclamos'] },
    { path: '../src/modules/reclamos/' + 'ReclamosBackoffice', names: ['default', 'ReclamosBackoffice'] },
    { path: '../src/modules/reclamos/' + 'AdminReclamos', names: ['default', 'AdminReclamos'] },
  ];
}

async function setSession(token: string, usuario: Record<string, unknown>) {
  localStorage.setItem('access_token', token);
  try {
    const store = await import(/* @vite-ignore */ '../src/store/' + 'useAuthStore');
    store.useAuthStore?.getState?.()?.setSession?.(token, usuario);
  } catch {
    // La pantalla puede autenticarse solo con el token de localStorage.
  }
}

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
  (globalThis as any).__hu09ReclamosHarness = freshHarness();
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

function mockReclamosFetch() {
  const h = harness();
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();

    if (/\/api\/v1\/reclamos\/\d+\/reembolso/.test(url)) {
      return ok({ detail: 'Política estricta de cero reembolsos' }, 405);
    }
    if (/\/api\/v1\/reclamos\/\d+$/.test(url) && method === 'GET') {
      const id = Number(url.match(/\/reclamos\/(\d+)$/)?.[1]);
      return ok(h.reclamos.find((r) => r.id === id) ?? {});
    }
    if (/\/api\/v1\/reclamos(\?|$)/.test(url) && method === 'POST') {
      if (h.postStatus >= 400) {
        return ok({ detail: h.postDetail }, h.postStatus);
      }
      return ok(
        {
          id: 99,
          pedido_origen_numero: PEDIDO,
          pedido_reposicion_numero: 'BL-REP-10045',
          producto_id: 55,
          estado: 'aprobado',
          intentos_adicionales_realizados: 0,
          creado_en: '2026-11-27T03:00:00',
        },
        h.postStatus,
      );
    }
    if (/\/api\/v1\/reclamos(\?|$)/.test(url)) {
      let items = [...h.reclamos];
      const estado = url.match(/[?&]estado=([^&]+)/)?.[1];
      const pedido = url.match(/[?&]pedido_numero=([^&]+)/)?.[1];
      if (estado) {
        items = items.filter(
          (r) => r.estado === decodeURIComponent(estado),
        );
      }
      if (pedido) {
        items = items.filter(
          (r) => r.pedido_origen_numero === decodeURIComponent(pedido),
        );
      }
      return ok(items);
    }
    if (/\/api\/v1\/pedidos\/[^/]+$/.test(url)) {
      return ok(h.pedido);
    }
    if (url.includes('/api/v1/auth/me')) {
      return ok(
        h.reclamos === (globalThis as any).__hu09ReclamosHarness.reclamos
          ? { id: 1, email: 'cliente@ejemplo.com', rol: 'cliente' }
          : { id: 1, email: 'admin@ejemplo.com', rol: 'admin' },
      );
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
          <Route path="/reclamos/nuevo" element={<Module />} />
          <Route path="/reclamos" element={<Module />} />
          <Route path="/backoffice/reclamos" element={<Module />} />
          <Route path="*" element={<Module />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function texto(): string {
  return (document.body.textContent ?? '').toLowerCase();
}

function primerCampoMotivo(): HTMLElement | null {
  return (
    (document.querySelector('#motivo') as HTMLElement | null) ||
    (document.querySelector('[name="motivo"]') as HTMLElement | null) ||
    (document.querySelector('textarea') as HTMLElement | null) ||
    null
  );
}

function archivoInputs(): HTMLInputElement[] {
  return Array.from(document.querySelectorAll('input[type="file"]'));
}

async function puedeEnviar() {
  const botones = screen.queryAllByRole('button', { name: /registrar|enviar|reclamar/i });
  if (botones.length > 0) {
    fireEvent.click(botones[0]);
    return;
  }
  const form = document.querySelector('form');
  if (form) fireEvent.submit(form);
}

describe('HU-09 formulario /reclamos/nuevo — registro con evidencias', () => {
  it('precarga el pedido y exige motivo y las dos evidencias', async () => {
    await setSession('token-cliente-hu09', {
      id: 9,
      email: 'cliente@ejemplo.com',
      rol: 'cliente',
    });
    Module = await loadModule(newClaimCandidates());
    if (!Module) importError = new Error('Ninguna pantalla de /reclamos/nuevo existe todavía');
    assertLoaded('/reclamos/nuevo');

    mockReclamosFetch();
    renderAt(`/reclamos/nuevo?pedido_numero=${PEDIDO}`);

    await waitFor(() => {
      const prefilled =
        screen.queryAllByDisplayValue(PEDIDO).length > 0 ||
        screen.queryAllByText(new RegExp(PEDIDO)).length > 0 ||
        texto().includes(PEDIDO.toLowerCase());
      expect(prefilled, 'El formulario debe tomar pedido_numero de la URL').toBe(true);
    });

    expect(texto()).toContain('motivo');
    expect(archivoInputs().length).toBeGreaterThanOrEqual(2);
    expect(
      screen.queryAllByRole('button', { name: /registrar|enviar|reclamar/i }).length,
    ).toBeGreaterThan(0);
  });

  it('envía el reclamo por multipart con pedido, motivo y las dos evidencias', async () => {
    await setSession('token-cliente-hu09', {
      id: 9,
      email: 'cliente@ejemplo.com',
      rol: 'cliente',
    });
    Module = await loadModule(newClaimCandidates());
    if (!Module) importError = new Error('Ninguna pantalla de /reclamos/nuevo existe todavía');
    assertLoaded('/reclamos/nuevo');

    const fetchMock = mockReclamosFetch();
    renderAt(`/reclamos/nuevo?pedido_numero=${PEDIDO}`);
    await waitFor(() => expect(archivoInputs().length).toBeGreaterThanOrEqual(2));

    const motivo = primerCampoMotivo();
    if (motivo) fireEvent.change(motivo, { target: { value: 'Producto dañado' } });

    const producto = document.querySelector('#producto_id') as
      | HTMLInputElement
      | HTMLSelectElement
      | null;
    if (producto) {
      const valor =
        producto instanceof HTMLSelectElement
          ? producto.options[producto.options.length - 1]?.value || '55'
          : '55';
      fireEvent.change(producto, { target: { value: valor } });
    }

    const inputs = archivoInputs();
    const fotoProducto = new File(['jpeg'], 'producto.jpg', { type: 'image/jpeg' });
    const fotoComprobante = new File(['pdf'], 'comprobante.pdf', {
      type: 'application/pdf',
    });
    fireEvent.change(inputs[0], { target: { files: [fotoProducto] } });
    fireEvent.change(inputs[1], { target: { files: [fotoComprobante] } });

    await puedeEnviar();

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          /\/api\/v1\/reclamos(\?|$)/.test(String(url)) &&
          (init?.method ?? 'GET').toUpperCase() === 'POST',
      );
      expect(call, 'Debe enviar POST /api/v1/reclamos').toBeTruthy();
      expect(call![1]!.body instanceof FormData).toBe(true);
      const form = call![1]!.body as FormData;
      expect(String(form.get('pedido_numero') ?? '')).toContain(PEDIDO);
      expect(String(form.get('motivo') ?? '')).not.toBe('');
      expect(form.get('foto_producto')).toBeTruthy();
      expect(form.get('foto_comprobante')).toBeTruthy();
    });
  });
});

describe('HU-09 historial /reclamos — consulta del cliente', () => {
  it('muestra los reclamos del cliente con su estado', async () => {
    await setSession('token-cliente-hu09', {
      id: 9,
      email: 'cliente@ejemplo.com',
      rol: 'cliente',
    });
    Module = await loadModule(historyCandidates());
    if (!Module) importError = new Error('Ninguna pantalla de /reclamos existe todavía');
    assertLoaded('/reclamos');

    harness().reclamos = [RECLAMO_1, { ...RECLAMO_2, estado: 'cerrado_exitoso' }];
    mockReclamosFetch();
    renderAt('/reclamos');

    await waitFor(() =>
      expect((screen.queryAllByText(new RegExp(PEDIDO)).length ?? 0)).toBeGreaterThan(0),
    );
    expect(screen.queryAllByText(/aprobado/i).length).toBeGreaterThan(0);
    expect(screen.queryAllByText(/cerrad/i).length).toBeGreaterThan(0);
  });
});

describe('HU-09 panel /backoffice/reclamos — supervisión y filtros', () => {
  it('muestra todos los reclamos y las incidencias escaladas', async () => {
    await setSession('token-admin-hu09', {
      id: 1,
      email: 'admin@ejemplo.com',
      rol: 'admin',
    });
    Module = await loadModule(backofficeCandidates());
    if (!Module)
      importError = new Error('Ninguna pantalla de /backoffice/reclamos existe todavía');
    assertLoaded('/backoffice/reclamos');

    mockReclamosFetch();
    renderAt('/backoffice/reclamos');

    await waitFor(() =>
      expect(screen.queryAllByText(new RegExp(PEDIDO)).length).toBeGreaterThan(0),
    );
    expect(screen.queryAllByText(/10046/).length).toBeGreaterThan(0);
    expect(texto()).toMatch(/supervisi/);
  });

  it('filtra por estado escalado_supervision', async () => {
    await setSession('token-admin-hu09', {
      id: 1,
      email: 'admin@ejemplo.com',
      rol: 'admin',
    });
    Module = await loadModule(backofficeCandidates());
    if (!Module)
      importError = new Error('Ninguna pantalla de /backoffice/reclamos existe todavía');
    assertLoaded('/backoffice/reclamos');

    const fetchMock = mockReclamosFetch();
    renderAt('/backoffice/reclamos');
    await waitFor(() =>
      expect(screen.queryAllByText(new RegExp(PEDIDO)).length).toBeGreaterThan(0),
    );

    const option = Array.from(document.querySelectorAll('option')).find(
      (opt) => opt.value === 'escalado_supervision',
    );
    if (option?.parentElement) {
      fireEvent.change(option.parentElement, {
        target: { value: 'escalado_supervision' },
      });
    } else {
      const boton = screen
        .queryAllByRole('button', { name: /escalad/i })
        .concat(screen.queryAllByRole('button', { name: /estado/i }))
        .shift();
      if (boton) fireEvent.click(boton);
    }

    const aplicar = screen.queryAllByRole('button', { name: /filtrar|aplicar|buscar/i })[0];
    if (aplicar) {
      fireEvent.click(aplicar);
    } else {
      const form = document.querySelector('form');
      if (form) fireEvent.submit(form);
    }

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes('estado=escalado_supervision'),
        ),
      ).toBe(true),
    );
  });
});
