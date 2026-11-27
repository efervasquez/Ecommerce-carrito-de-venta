import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// Fuente de verdad: contratos/CONTRATO-HU-01.md (v1) §3.5 y §4.
// Pantalla de login: inputs email/password, boton "Iniciar sesion" y mensaje de
// error ante 401.

const MSG_LOGIN_FALLO = 'Credenciales inválidas o cuenta no activada.';

let Login: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  Login = null;
  try {
    const mod = await import('../src/pages/Login');
    Login = (mod as any).default ?? (mod as any).Login ?? null;
  } catch (e) {
    importError = e;
  }
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/login']}>
          <Login />
        </MemoryRouter>
      </QueryClientProvider>
    ),
  };
}

function assertLoaded() {
  expect(importError, `Componente Login no implementado: ${importError}`).toBeNull();
  expect(Login, 'Componente Login no resuelto (export default/named)').not.toBeNull();
}

describe('HU-01 /login — contrato CONTRATO-HU-01.md v1', () => {
  it('renderiza inputs email/password y boton "Iniciar sesion"', () => {
    assertLoaded();
    const { container } = renderLogin();

    expect(container.querySelector('input[name="email"]')).not.toBeNull();
    expect(container.querySelector('input[name="password"]')).not.toBeNull();

    expect(screen.getByRole('button', { name: 'Iniciar sesión' })).not.toBeNull();
  });

  it('envia POST /api/v1/auth/login con email y password', async () => {
    assertLoaded();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        access_token: 'jwt-de-prueba',
        token_type: 'bearer',
        expires_in: 3600,
        usuario: { id: 1, email: 'cliente.nuevo@ejemplo.com', rol: 'cliente' },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { container } = renderLogin();
    fireEvent.change(container.querySelector('input[name="email"]') as HTMLInputElement, {
      target: { value: 'cliente.nuevo@ejemplo.com' },
    });
    fireEvent.change(container.querySelector('input[name="password"]') as HTMLInputElement, {
      target: { value: 'Password123!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain('/api/v1/auth/login');
    const body = JSON.parse(String(options.body));
    expect(body.email).toBe('cliente.nuevo@ejemplo.com');
    expect(body.password).toBe('Password123!');

    // Al recibir 200 no debe mostrarse mensaje de error.
    await waitFor(() => {
      expect(screen.queryByText(MSG_LOGIN_FALLO)).toBeNull();
    });
  });

  it('ante 401 muestra mensaje de error en pantalla', async () => {
    assertLoaded();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: MSG_LOGIN_FALLO }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const { container } = renderLogin();
    fireEvent.change(container.querySelector('input[name="email"]') as HTMLInputElement, {
      target: { value: 'cliente.nuevo@ejemplo.com' },
    });
    fireEvent.change(container.querySelector('input[name="password"]') as HTMLInputElement, {
      target: { value: 'PasswordErronea123!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }));

    await waitFor(() => {
      expect(screen.queryByText(MSG_LOGIN_FALLO)).not.toBeNull();
    });
  });
});
