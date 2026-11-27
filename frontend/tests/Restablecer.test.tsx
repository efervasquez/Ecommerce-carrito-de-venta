import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

let Restablecer: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  Restablecer = null;
  try {
    const mod = await import('../src/pages/Restablecer');
    Restablecer = (mod as any).default ?? (mod as any).Restablecer ?? null;
  } catch (error) {
    importError = error;
  }
});

afterEach(() => vi.unstubAllGlobals());

function renderRestablecer(entry: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entry]}>
        <Restablecer />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('HU-02 /restablecer — contrato CONTRATO-HU-02.md v1', () => {
  it('renderiza password/confirm_password y boton "Actualizar contraseña"', () => {
    expect(importError).toBeNull();
    expect(Restablecer).not.toBeNull();
    const { container } = renderRestablecer('/restablecer?token=TOKEN-DE-PRUEBA');
    expect(container.querySelector('input[name="password"]')).not.toBeNull();
    expect(container.querySelector('input[name="confirm_password"]')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Actualizar contraseña' })).not.toBeNull();
  });

  it('extrae token del query y envia POST /api/v1/auth/restablecer', async () => {
    expect(importError).toBeNull();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: 'Contraseña actualizada correctamente' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const { container } = renderRestablecer('/restablecer?token=TOKEN-DE-PRUEBA');
    fireEvent.change(container.querySelector('input[name="password"]') as HTMLInputElement, {
      target: { value: 'NuevaClave2026!' },
    });
    fireEvent.change(container.querySelector('input[name="confirm_password"]') as HTMLInputElement, {
      target: { value: 'NuevaClave2026!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar contraseña' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain('/api/v1/auth/restablecer');
    expect(JSON.parse(String(options.body))).toEqual({
      token: 'TOKEN-DE-PRUEBA',
      password: 'NuevaClave2026!',
    });
    await waitFor(() => {
      const loginLink = screen.queryByRole('link', { name: /login|iniciar sesión/i });
      expect(loginLink).not.toBeNull();
      expect(loginLink?.getAttribute('href')).toBe('/login');
    });
  });

  it('token invalido bloquea el formulario y ofrece "Solicitar nuevo enlace" hacia /recuperar', async () => {
    expect(importError).toBeNull();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'El enlace es inválido o ha expirado.' }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const { container } = renderRestablecer('/restablecer?token=TOKEN-INVALIDO');

    fireEvent.change(container.querySelector('input[name="password"]') as HTMLInputElement, {
      target: { value: 'NuevaClave2026!' },
    });
    fireEvent.change(container.querySelector('input[name="confirm_password"]') as HTMLInputElement, {
      target: { value: 'NuevaClave2026!' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar contraseña' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const requestLink = await screen.findByRole('link', { name: 'Solicitar nuevo enlace' });
    expect(requestLink.getAttribute('href')).toBe('/recuperar');
    expect(container.querySelector('input[name="password"]')).toBeNull();
    expect(container.querySelector('input[name="confirm_password"]')).toBeNull();
  });
});
