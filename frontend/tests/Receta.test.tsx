import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const LOW_CONFIDENCE_MESSAGE =
  'No pudimos leer la receta con suficiente confianza. Revisa y confirma los medicamentos';
const ERROR_MESSAGE = 'No se pudo procesar la receta. Intenta nuevamente';

type OcrPhase = 'completado' | 'requiere_validacion' | 'sin_stock' | 'error';

type OcrHarness = {
  phase: OcrPhase;
  items: { producto_id: number; nombre: string; cantidad: number }[];
  suggested: { texto: string; producto_id: number | null; cantidad: number; confianza: number }[];
  faltantes: { nombre: string; solicitado: number; disponible: number }[];
};

function harness(): OcrHarness {
  return (globalThis as any).__hu06Harness as OcrHarness;
}

let LeerReceta: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.resetModules();
  vi.clearAllMocks();
  (globalThis as any).__hu06Harness = {
    phase: 'completado',
    items: [{ producto_id: 1, nombre: 'Medicamento leído', cantidad: 1 }],
    suggested: [
      { texto: 'Medicamento dudoso', producto_id: 1, cantidad: 2, confianza: 55 },
    ],
    faltantes: [{ nombre: 'Medicamento faltante', solicitado: 2, disponible: 0 }],
  } satisfies OcrHarness;

  importError = null;
  LeerReceta = null;
  const candidates = [
    { path: '../src/pages/' + 'Receta', names: ['default', 'Receta', 'LeerReceta'] },
    { path: '../src/pages/' + 'Carrito', names: ['default', 'Carrito'] },
  ];
  for (const candidate of candidates) {
    try {
      const mod = await import(/* @vite-ignore */ candidate.path);
      for (const name of candidate.names) {
        if (mod[name]) {
          LeerReceta = mod[name];
          break;
        }
      }
    } catch {
      // Se prueba la siguiente pantalla candidata.
    }
    if (LeerReceta) break;
  }
  if (!LeerReceta) {
    importError = new Error('Ninguna pantalla expone el botón Leer receta todavía');
  }
});

afterEach(() => vi.unstubAllGlobals());

function assertLoaded() {
  expect(importError, `Pantalla de lectura de receta no implementada: ${importError}`).toBeNull();
  expect(LeerReceta).not.toBeNull();
}

function jobResult() {
  const h = harness();
  const base = { receta_id: 77 };
  switch (h.phase) {
    case 'completado':
      return { ...base, estado: 'completado', items: h.items };
    case 'requiere_validacion':
      return {
        ...base,
        estado: 'requiere_validacion',
        items_sugeridos: h.suggested,
        confianza: 55,
        mensaje: LOW_CONFIDENCE_MESSAGE,
      };
    case 'sin_stock':
      return {
        ...base,
        estado: 'sin_stock',
        faltantes: h.faltantes,
        mensaje: `Lo sentimos, no contamos con stock disponible de ${h.faltantes[0].nombre} para completar su receta médica`,
      };
    case 'error':
      return { estado: 'error', mensaje: ERROR_MESSAGE };
  }
}

function mockOcrFetch() {
  let polls = 0;
  const ok = (body: unknown, status = 200) =>
    Promise.resolve({ ok: status < 400, status, json: async () => body });
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();
    if (url.includes('/api/v1/carrito')) {
      return ok({
        items_oferta: [],
        items_regulares: [],
        subtotal: 0,
        ahorro_total: 0,
        total: 0,
        reserva_expira_en: null,
      });
    }
    if (url.includes('/api/v1/ocr/recetas') && method === 'POST') {
      return ok(
        { job_id: 'job_test', estado: 'procesando', poll_interval_ms: 1500 },
        202,
      );
    }
    if (url.includes('/api/v1/ocr/jobs') && method === 'POST') {
      return ok({ receta_id: 77, estado: 'completado', items: harness().items });
    }
    if (url.includes('/api/v1/ocr/jobs')) {
      polls += 1;
      if (polls === 1) return ok({ estado: 'procesando' });
      return ok(jobResult());
    }
    return ok({});
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderReceta() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/carrito']}>
        <Routes>
          <Route path="/carrito" element={<LeerReceta />} />
          <Route path="*" element={<LeerReceta />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function uploadAndStart() {
  renderReceta();
  const button = await screen.findByRole('button', { name: /Leer receta/i });
  const fileInput = document.querySelector('input[type="file"]');
  if (fileInput) {
    fireEvent.change(fileInput, {
      target: { files: [new File(['contenido'], 'receta_ok.jpg', { type: 'image/jpeg' })] },
    });
  }
  fireEvent.click(button);
  return button;
}

describe('HU-06 Lectura de receta (OCR)', () => {
  it('muestra el botón Leer receta', async () => {
    assertLoaded();
    mockOcrFetch();
    renderReceta();
    expect(await screen.findByRole('button', { name: /Leer receta/i })).not.toBeNull();
  });

  it('sube el archivo, sondea el job y en completado vuelve al carrito', async () => {
    assertLoaded();
    harness().phase = 'completado';
    const fetchMock = mockOcrFetch();
    await uploadAndStart();
    await waitFor(
      () =>
        expect(
          fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/ocr/recetas')),
        ).toBe(true),
      { timeout: 4000 },
    );
    await waitFor(
      () =>
        expect(
          fetchMock.mock.calls.some(([url]) => String(url).includes('/api/v1/ocr/jobs/job_test')),
        ).toBe(true),
      { timeout: 5000 },
    );
    expect(window.location.pathname === '/login').toBe(false);
  });

  it('requiere_validacion abre la validación asistida', async () => {
    assertLoaded();
    harness().phase = 'requiere_validacion';
    mockOcrFetch();
    await uploadAndStart();
    await waitFor(() => expect(screen.getByText(LOW_CONFIDENCE_MESSAGE)).not.toBeNull(), {
      timeout: 5000,
    });
    expect(screen.getByText(harness().suggested[0].texto)).not.toBeNull();
  });

  it('sin_stock muestra la alerta con el faltante sin redirigir', async () => {
    assertLoaded();
    harness().phase = 'sin_stock';
    mockOcrFetch();
    await uploadAndStart();
    const expected = `Lo sentimos, no contamos con stock disponible de ${harness().faltantes[0].nombre} para completar su receta médica`;
    await waitFor(() => expect(screen.getByText(expected)).not.toBeNull(), { timeout: 5000 });
    expect(screen.getByRole('button', { name: /Leer receta/i })).not.toBeNull();
  });

  it('error muestra el mensaje de reintento', async () => {
    assertLoaded();
    harness().phase = 'error';
    mockOcrFetch();
    await uploadAndStart();
    await waitFor(() => expect(screen.getByText(ERROR_MESSAGE)).not.toBeNull(), { timeout: 5000 });
  });
});
