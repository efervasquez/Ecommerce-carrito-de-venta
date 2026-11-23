export interface UsuarioPublico {
  id: number;
  email: string;
  rol: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  usuario: UsuarioPublico;
}

export interface MensajeResponse {
  message: string;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : `Error ${response.status}`;
    throw new ApiError(response.status, detail);
  }

  return body as T;
}

export function solicitarRegistro(email: string): Promise<MensajeResponse> {
  return request<MensajeResponse>('/auth/registro', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function activarCuenta(token: string, password: string): Promise<MensajeResponse> {
  return request<MensajeResponse>('/auth/activar', {
    method: 'POST',
    body: JSON.stringify({ token, password }),
  });
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function solicitarRecuperacion(email: string): Promise<MensajeResponse> {
  return request<MensajeResponse>('/auth/recuperar', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function restablecerContrasena(
  token: string,
  password: string,
): Promise<MensajeResponse> {
  return request<MensajeResponse>('/auth/restablecer', {
    method: 'POST',
    body: JSON.stringify({ token, password }),
  });
}
