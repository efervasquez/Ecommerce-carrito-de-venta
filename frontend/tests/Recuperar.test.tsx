import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

const MSG_RECUPERAR = 'Si el email existe, recibirás un correo';

let Recuperar: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  vi.restoreAllMocks();
  importError = null;
  Recuperar = null;
  try {
    const mod = await import('../src/pages/Recuperar');
    Recuperar = (mod as any).default ?? (mod as any).Recuperar ?? null;
  } catch (error) {
    importError = error;
  }
});

afterEach(() => vi.unstubAllGlobals());

function renderRecuperar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/recuperar']}>
        <Recuperar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('HU-02 /recuperar — contrato CONTRATO-HU-02.md v1', () => {
  it('renderiza input email y boton "Enviar enlace"', () => {
    expect(importError).toBeNull();
    expect(Recuperar).not.toBeNull();
    const { container } = renderRecuperar();
    expect(container.querySelector('input[name="email"]')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Enviar enlace' })).not.toBeNull();
  });

  it('envia POST /api/v1/auth/recuperar con email y muestra el mensaje generico', async () => {
    expect(importError).toBeNull();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: MSG_RECUPERAR }),
    });
    vi.stubGlobal('fetch', fetchMock);
    const { container } = renderRecuperar();
    fireEvent.change(container.querySelector('input[name="email"]') as HTMLInputElement, {
      target: { value: 'cliente@ejemplo.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(String(url)).toContain('/api/v1/auth/recuperar');
    expect(String(options.method).toUpperCase()).toBe('POST');
    expect(JSON.parse(String(options.body))).toEqual({ email: 'cliente@ejemplo.com' });
    await waitFor(() => expect(screen.queryByText(MSG_RECUPERAR)).not.toBeNull());
  });
});
