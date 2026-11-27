import React from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

let Login: React.ComponentType<any> | null = null;
let importError: unknown = null;

beforeEach(async () => {
  importError = null;
  Login = null;
  try {
    const mod = await import('../src/pages/Login');
    Login = (mod as any).default ?? (mod as any).Login ?? null;
  } catch (error) {
    importError = error;
  }
});

function renderLogin() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/login']}>
        <Login />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('HU-02 /login — enlace de recuperación', () => {
  it('muestra el enlace exacto y apunta a /recuperar', () => {
    expect(importError).toBeNull();
    expect(Login).not.toBeNull();
    renderLogin();
    const link = screen.getByRole('link', { name: '¿Olvidaste tu contraseña?' });
    expect(link).not.toBeNull();
    expect(link.getAttribute('href')).toBe('/recuperar');
  });
});
