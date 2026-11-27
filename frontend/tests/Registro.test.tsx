import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// Fuente de verdad: contratos/CONTRATO-HU-01.md (v1) §3.5 y §4.
// Prueba de caja negra de la pantalla de registro. No asume estructura interna:
// solo verifica elementos observables (input name/id, texto de boton, mensajes
// visibles) y la llamada HTTP a la ruta del contrato.

const MSG_REGISTRO = 'Si el correo ingresado es válido, recibirás un enlace de activación en tu buzón.';

let Registro: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  Registro = null;
  try {
    const mod = await import('../src/pages/Registro');
    Registro = (mod as any).default ?? (mod as any).Registro ?? null;
  } catch (e) {
    importError = e;
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderRegistro() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/registro']}>
          <Registro />
        </MemoryRouter>
      </QueryClientProvider>
    ),
  };
}

function assertLoaded() {
  expect(importError, `Componente Registro no implementado: ${importError}`).toBeNull();
  expect(Registro, 'Componente Registro no resuelto (export default/named)').not.toBeNull();
}

describe('HU-01 /registro — contrato CONTRATO-HU-01.md v1', () => {
  it('renderiza input email y boton "Registrarme"', () => {
    assertLoaded();
    const { container } = renderRegistro();

    const emailInput =
      container.querySelector('input[name="email"]') ??
      container.querySelector('input#email');
    expect(emailInput, 'Debe existir un input con name/id "email"').not.toBeNull();

    const button = screen.getByRole('button', { name: 'Registrarme' });
    expect(button, 'Debe existir boton con texto "Registrarme"').not.toBeNull();
  });

  it('envia POST /api/v1/auth/registro con campo email y muestra el mensaje de exito', async () => {
    assertLoaded();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: MSG_REGISTRO }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { container } = renderRegistro();
    const input = container.querySelector('input[name="email"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'cliente.nuevo@ejemplo.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Registrarme' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain('/api/v1/auth/registro');
    expect(options.method === undefined || String(options.method).toUpperCase() === 'POST').toBe(true);
    expect(JSON.parse(String(options.body)).email).toBe('cliente.nuevo@ejemplo.com');

    await waitFor(() => {
      expect(screen.queryByText(MSG_REGISTRO)).not.toBeNull();
    });
  });

  it('email invalido muestra error visual sin enviar la peticion', () => {
    assertLoaded();
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const { container } = renderRegistro();
    const input = container.querySelector('input[name="email"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'correo_sin_dominio.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Registrarme' }));

    // "sin enviar la peticion"
    expect(fetchMock, 'No debe enviarse la peticion con email invalido').not.toHaveBeenCalled();

    // no debe mostrarse el mensaje de exito
    expect(screen.queryByText(MSG_REGISTRO)).toBeNull();

    // debe existir un indicador visual de error en el campo (aria-invalid o role=alert)
    const hasError =
      input.getAttribute('aria-invalid') === 'true' ||
      container.querySelector('[role="alert"]') !== null ||
      container.querySelector('[data-testid*="error"]') !== null;
    expect(hasError, 'Debe mostrarse un error visual en el campo').toBe(true);
  });
});
