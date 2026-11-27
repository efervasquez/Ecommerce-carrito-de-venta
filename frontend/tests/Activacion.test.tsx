import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// Fuente de verdad: contratos/CONTRATO-HU-01.md (v1) §3.5 y §4.
// Pantalla de activacion: inputs password/confirm_password, boton "Activar cuenta",
// extrae el query param token y muestra los mensajes visibles del contrato.

const MSG_OK = 'Cuenta activada exitosamente';
const MSG_INVALIDO = 'El enlace de activación es inválido o ha expirado';

let Activar: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  Activar = null;
  try {
    const mod = await import('../src/pages/Activar');
    Activar = (mod as any).default ?? (mod as any).Activar ?? null;
  } catch (e) {
    importError = e;
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderActivar(initialEntry = '/activar') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Activar />
        </MemoryRouter>
      </QueryClientProvider>
    ),
  };
}

function assertLoaded() {
  expect(importError, `Componente Activar no implementado: ${importError}`).toBeNull();
  expect(Activar, 'Componente Activar no resuelto (export default/named)').not.toBeNull();
}

describe('HU-01 /activar — contrato CONTRATO-HU-01.md v1', () => {
  it('renderiza inputs password/confirm_password y boton "Activar cuenta"', () => {
    assertLoaded();
    const { container } = renderActivar();

    expect(container.querySelector('input[name="password"]')).not.toBeNull();
    expect(container.querySelector('input[name="confirm_password"]')).not.toBeNull();

    expect(screen.getByRole('button', { name: 'Activar cuenta' })).not.toBeNull();
  });

  it('extrae el query param token y envia POST /api/v1/auth/activar con token y password', async () => {
    assertLoaded();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: 'Cuenta activada exitosamente. Ya puedes iniciar sesión.' }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { container } = renderActivar('/activar?token=TOKEN-DE-PRUEBA');
    fireEvent.change(container.querySelector('input[name="password"]') as HTMLInputElement, {
      target: { value: 'Password123!' },
    });
    fireEvent.change(container.querySelector('input[name="confirm_password"]') as HTMLInputElement, {
      target: { value: 'Password123!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Activar cuenta' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain('/api/v1/auth/activar');
    const body = JSON.parse(String(options.body));
    expect(body.token).toBe('TOKEN-DE-PRUEBA');
    expect(body.password).toBe('Password123!');

    await waitFor(() => {
      expect(screen.queryByText(MSG_OK)).not.toBeNull();
    });
  });

  it('token invalido muestra el mensaje de error del contrato', async () => {
    assertLoaded();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: MSG_INVALIDO }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { container } = renderActivar('/activar?token=TOKEN-INVALIDO');
    fireEvent.change(container.querySelector('input[name="password"]') as HTMLInputElement, {
      target: { value: 'Password123!' },
    });
    fireEvent.change(container.querySelector('input[name="confirm_password"]') as HTMLInputElement, {
      target: { value: 'Password123!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Activar cuenta' }));

    await waitFor(() => {
      expect(screen.queryByText(MSG_INVALIDO)).not.toBeNull();
    });
  });
});
