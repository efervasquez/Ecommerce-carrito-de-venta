import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const PRODUCTO_1 = {
  id: 55,
  nombre: 'Amoxicilina 500mg',
  componentes: 'Amoxicilina trihidrato',
  precio_regular: 12.5,
  moneda: 'PEN',
  descuento_porcentaje: 0,
  stock_disponible: 100,
  stock_reservado: 2,
  precios_bajos: false,
  requiere_receta: true,
  presentacion: 'Caja con 20 cápsulas',
  detalle: 'Antibiótico bactericida de amplio espectro.',
  metodos_entrega: ['delivery', 'retiro'],
  imagen_url: 'https://ejemplo.com/amoxicilina.png',
  contraindicaciones: 'Hipersensibilidad a penicilinas.',
  precauciones_advertencias: 'Ajustar dosis en insuficiencia renal.',
  reacciones_adversas: 'Náuseas, diarrea, erupción cutánea.',
};

const PRODUCTO_2 = {
  id: 56,
  nombre: 'Omeprazol 20mg',
  componentes: 'Omeprazol',
  precio_regular: 18,
  moneda: 'PEN',
  descuento_porcentaje: 15,
  stock_disponible: 40,
  stock_reservado: 0,
  precios_bajos: true,
  requiere_receta: false,
  presentacion: 'Frasco con 30 cápsulas',
  detalle: 'Inhibidor de la bomba de protones.',
  metodos_entrega: ['delivery', 'retiro'],
  imagen_url: 'https://ejemplo.com/omeprazol.png',
  contraindicaciones: 'Hipersensibilidad a omeprazol.',
  precauciones_advertencias: 'Consultar médico en embarazo.',
  reacciones_adversas: 'Cefalea, dolor abdominal.',
};

type Harness = {
  productos: Array<Record<string, unknown>>;
  detalle: Record<string, unknown>;
};

function harness(): Harness {
  return (globalThis as any).__hu10InventarioHarness as Harness;
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

function inventarioCandidates() {
  return [
    { path: '../src/pages/' + 'BackofficeInventario', names: ['default', 'BackofficeInventario'] },
    { path: '../src/pages/' + 'InventarioBackoffice', names: ['default', 'InventarioBackoffice'] },
    { path: '../src/pages/' + 'Inventario', names: ['default', 'Inventario'] },
  ];
}

function productoFormCandidates() {
  return [
    { path: '../src/pages/' + 'ProductoForm', names: ['default', 'ProductoForm'] },
    { path: '../src/pages/' + 'ProductoNuevo', names: ['default', 'ProductoNuevo'] },
    { path: '../src/pages/' + 'ProductoEditar', names: ['default', 'ProductoEditar'] },
    { path: '../src/pages/' + 'BackofficeProductoForm', names: ['default', 'BackofficeProductoForm'] },
  ];
}

async function setSession() {
  const token = 'token-admin-hu10';
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
  (globalThis as any).__hu10InventarioHarness = {
    productos: [PRODUCTO_1, PRODUCTO_2],
    detalle: PRODUCTO_1,
  } satisfies Harness;
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

function mockInventarioFetch() {
  const h = harness();
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();
    const body =
      init?.body && typeof init.body === 'string' ? JSON.parse(init.body) : {};

    if (/\/api\/v1\/backoffice\/productos\/\d+\/stock$/.test(url) && method === 'PATCH') {
      return ok({
        id: Number(url.match(/productos\/(\d+)\/stock/)?.[1]),
        producto_id: Number(url.match(/productos\/(\d+)\/stock/)?.[1]),
        disponible: body.stock_disponible,
        reservado: 2,
        actualizado_en: '2026-11-27T05:00:00',
      });
    }
    if (/\/api\/v1\/backoffice\/productos\/\d+$/.test(url) && method === 'PUT') {
      const id = Number(url.match(/productos\/(\d+)$/)?.[1]);
      return ok({ ...h.detalle, ...body, id });
    }
    if (/\/api\/v1\/backoffice\/productos\/\d+$/.test(url) && method === 'GET') {
      return ok(h.detalle);
    }
    if (/\/api\/v1\/backoffice\/productos$/.test(url) && method === 'POST') {
      return ok({ ...body, id: 99, stock_reservado: 0 }, 201);
    }
    if (/\/api\/v1\/backoffice\/productos(\?|$)/.test(url)) {
      let items = [...h.productos];
      const q = url.match(/[?&]q=([^&]*)/)?.[1];
      if (q) {
        const term = decodeURIComponent(q).toLowerCase();
        items = items.filter(
          (p) =>
            String(p.nombre).toLowerCase().includes(term) ||
            String(p.componentes).toLowerCase().includes(term),
        );
      }
      return ok({ items, total: items.length });
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
          <Route path="/backoffice/inventario" element={<Module />} />
          <Route path="/backoffice/inventario/nuevo" element={<Module />} />
          <Route path="/backoffice/inventario/:id/editar" element={<Module />} />
          <Route path="*" element={<Module />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function texto(): string {
  return (document.body.textContent ?? '').toLowerCase();
}

function campo(nombre: string): HTMLElement | null {
  return document.querySelector(`#${nombre}, [name="${nombre}"]`) as HTMLElement | null;
}

function escribir(nombre: string, valor: string): boolean {
  const el = campo(nombre);
  if (!el) return false;
  fireEvent.change(el, { target: { value: valor } });
  return true;
}

function botonGuardar(): HTMLElement | null {
  return (
    screen.queryAllByRole('button', {
      name: /guardar|registrar|crear|actualizar|editar|aceptar|enviar|modificar/i,
    })[0] ?? null
  );
}

async function enviarFormulario() {
  const boton = botonGuardar();
  if (boton) {
    fireEvent.click(boton);
    return;
  }
  const form = document.querySelector('form');
  if (form) fireEvent.submit(form);
}

describe('HU-10 /backoffice/inventario — existencias y ajuste rápido', () => {
  it('muestra la tabla de existencias con disponible y reservado', async () => {
    await setSession();
    Module = await loadModule(inventarioCandidates());
    if (!Module)
      importError = new Error('Ninguna pantalla de /backoffice/inventario existe todavía');
    assertLoaded('/backoffice/inventario');

    mockInventarioFetch();
    renderAt('/backoffice/inventario');

    expect((await screen.findAllByText(PRODUCTO_1.nombre)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(PRODUCTO_2.nombre).length).toBeGreaterThan(0);
    expect(texto()).toContain(String(PRODUCTO_1.stock_disponible));
    expect(texto()).toMatch(/disponible/);
    expect(texto()).toMatch(/reservad/);
  });

  it('busca por nombre o componente y consulta ?q=', async () => {
    await setSession();
    Module = await loadModule(inventarioCandidates());
    if (!Module)
      importError = new Error('Ninguna pantalla de /backoffice/inventario existe todavía');
    assertLoaded('/backoffice/inventario');

    const fetchMock = mockInventarioFetch();
    renderAt('/backoffice/inventario');
    await screen.findAllByText(PRODUCTO_1.nombre);

    const buscador =
      (document.querySelector('#q') as HTMLElement | null) ||
      (document.querySelector('[name="q"]') as HTMLElement | null) ||
      (document.querySelector('input[placeholder*="usca"]') as HTMLElement | null);
    expect(buscador, 'Debe existir el buscador de inventario').not.toBeNull();
    fireEvent.change(buscador!, { target: { value: 'Omeprazol' } });

    const botonBuscar = screen.queryAllByRole('button', {
      name: /buscar|filtrar/i,
    })[0];
    if (botonBuscar) {
      fireEvent.click(botonBuscar);
    } else {
      const form = buscador!.closest('form');
      if (form) fireEvent.submit(form);
    }

    await waitFor(() =>
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes('q=Omeprazol'),
        ),
      ).toBe(true),
    );
  });

  it('ajusta el stock disponible de una fila y lo guarda', async () => {
    await setSession();
    Module = await loadModule(inventarioCandidates());
    if (!Module)
      importError = new Error('Ninguna pantalla de /backoffice/inventario existe todavía');
    assertLoaded('/backoffice/inventario');

    const fetchMock = mockInventarioFetch();
    renderAt('/backoffice/inventario');
    const celda = (await screen.findAllByText(PRODUCTO_1.nombre))[0];
    const fila = celda.closest('tr') ?? celda.parentElement!;
    const inputs = within(fila as HTMLElement).queryAllByRole('spinbutton');
    expect(
      inputs.length,
      'La fila debe ofrecer un input rápido de stock',
    ).toBeGreaterThan(0);
    fireEvent.change(inputs[0], { target: { value: '50' } });

    const guardarFila =
      within(fila as HTMLElement).queryAllByRole('button', { name: /guardar|actualizar/i })[0] ??
      botonGuardar();
    expect(guardarFila, 'Debe existir un botón para guardar el ajuste').toBeTruthy();
    fireEvent.click(guardarFila!);

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          /\/api\/v1\/backoffice\/productos\/\d+\/stock$/.test(String(url)) &&
          (init?.method ?? 'GET').toUpperCase() === 'PATCH',
      );
      expect(call, 'Debe enviar PATCH .../stock').toBeTruthy();
      const payload = JSON.parse(String(call![1]!.body));
      expect(Number(payload.stock_disponible)).toBe(50);
      expect(String(call![0])).toContain(`/productos/${PRODUCTO_1.id}/stock`);
    });
  });
});

describe('HU-10 /backoffice/inventario/nuevo — alta de producto', () => {
  it('muestra los campos obligatorios y registra el producto', async () => {
    await setSession();
    Module = await loadModule(productoFormCandidates());
    if (!Module)
      importError = new Error('Ninguna pantalla de alta de producto existe todavía');
    assertLoaded('/backoffice/inventario/nuevo');

    const fetchMock = mockInventarioFetch();
    renderAt('/backoffice/inventario/nuevo');
    await waitFor(() => expect(document.querySelector('form')).not.toBeNull());

    for (const requerido of [
      'nombre',
      'componentes',
      'precio_regular',
      'presentacion',
      'detalle',
      'stock_disponible',
    ]) {
      expect(campo(requerido), `Falta el campo obligatorio '${requerido}'`).not.toBeNull();
    }

    const nombre = 'HU10-Nuevo-Producto';
    escribir('nombre', nombre);
    escribir('componentes', 'HU10-Components');
    escribir('precio_regular', '12.5');
    escribir('presentacion', 'Caja con 20 cápsulas');
    escribir('detalle', 'Detalle de prueba HU-10.');
    escribir('stock_disponible', '100');
    escribir('contraindicaciones', 'Ninguna.');
    escribir('precauciones_advertencias', 'Ninguna.');
    escribir('reacciones_adversas', 'Ninguna.');

    for (const metodo of ['delivery', 'retiro']) {
      const check = document.querySelector(
        `input[type="checkbox"][name="${metodo}"], input[type="checkbox"]#${metodo}`,
      ) as HTMLInputElement | null;
      if (check && !check.checked) fireEvent.click(check);
    }

    await enviarFormulario();

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          /\/api\/v1\/backoffice\/productos$/.test(String(url)) &&
          (init?.method ?? 'GET').toUpperCase() === 'POST',
      );
      expect(call, 'Debe enviar POST /api/v1/backoffice/productos').toBeTruthy();
      const payload = JSON.parse(String(call![1]!.body));
      expect(payload.nombre).toBe(nombre);
      expect(payload.componentes).toBe('HU10-Components');
      expect(Number(payload.precio_regular)).toBe(12.5);
      expect(payload.presentacion).toBe('Caja con 20 cápsulas');
      expect(payload.detalle).toBe('Detalle de prueba HU-10.');
      expect(Number(payload.stock_disponible)).toBe(100);
      expect(Array.isArray(payload.metodos_entrega)).toBe(true);
      expect(payload.metodos_entrega.length).toBeGreaterThan(0);
      for (const metodo of payload.metodos_entrega) {
        expect(['delivery', 'retiro']).toContain(metodo);
      }
    });
  });
});

describe('HU-10 /backoffice/inventario/:id/editar — edición integral', () => {
  it('edita precio, descuento y activa la etiqueta Precios bajos', async () => {
    await setSession();
    Module = await loadModule(productoFormCandidates());
    if (!Module)
      importError = new Error('Ninguna pantalla de edición de producto existe todavía');
    assertLoaded('/backoffice/inventario/:id/editar');

    const fetchMock = mockInventarioFetch();
    renderAt(`/backoffice/inventario/${PRODUCTO_1.id}/editar`);

    await waitFor(() =>
      expect(screen.queryAllByDisplayValue(PRODUCTO_1.nombre).length).toBeGreaterThan(0),
    );

    const nuevoNombre = 'HU10-Omeprazol Editado';
    escribir('nombre', nuevoNombre);
    escribir('precio_regular', '18');
    escribir('descuento_porcentaje', '15');

    const preciosBajos = document.querySelector(
      'input[type="checkbox"]#precios_bajos, input[type="checkbox"][name="precios_bajos"]',
    ) as HTMLInputElement | null;
    expect(
      preciosBajos,
      'La edición debe ofrecer el selector manual de Precios bajos',
    ).not.toBeNull();
    if (!preciosBajos!.checked) fireEvent.click(preciosBajos!);

    await enviarFormulario();

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(
        ([url, init]) =>
          new RegExp(`/api/v1/backoffice/productos/${PRODUCTO_1.id}$`).test(String(url)) &&
          (init?.method ?? 'GET').toUpperCase() === 'PUT',
      );
      expect(call, 'Debe enviar PUT /api/v1/backoffice/productos/{id}').toBeTruthy();
      const payload = JSON.parse(String(call![1]!.body));
      expect(payload.nombre).toBe(nuevoNombre);
      expect(Number(payload.precio_regular)).toBe(18);
      expect(Number(payload.descuento_porcentaje)).toBe(15);
      expect(payload.precios_bajos).toBe(true);
    });
  });
});
