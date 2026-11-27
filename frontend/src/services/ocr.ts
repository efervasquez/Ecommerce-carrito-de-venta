export interface JobCreado {
  job_id: number;
  estado: string;
  poll_interval_ms: number;
}

export interface ItemReceta {
  producto_id: number;
  nombre: string;
  cantidad: number;
}

export interface ItemSugerido {
  texto: string;
  producto_id: number | null;
  cantidad: number;
  confianza: number;
}

export interface Faltante {
  nombre: string;
  solicitado: number;
  disponible: number;
}

export interface JobEstado {
  estado: string;
  receta_id?: string | null;
  items?: ItemReceta[];
  items_sugeridos?: ItemSugerido[];
  faltantes?: Faltante[];
  confianza?: number | null;
  mensaje?: string | null;
}

export class OcrApiError extends Error {
  status: number;
  body: JobEstado | null;

  constructor(status: number, detail: string, body: JobEstado | null) {
    super(detail);
    this.status = status;
    this.body = body;
  }
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
  });
  const body = (await response.json()) as T & { detail?: string };
  if (!response.ok) {
    throw new OcrApiError(
      response.status,
      body?.detail ?? 'No se pudo completar la solicitud.',
      (body as unknown as JobEstado) ?? null,
    );
  }
  return body as T;
}

export function subirReceta(archivo: File): Promise<JobCreado> {
  const datos = new FormData();
  datos.append('archivo', archivo);
  return request<JobCreado>('/ocr/recetas', { method: 'POST', body: datos });
}

export function getJob(jobId: number): Promise<JobEstado> {
  return request<JobEstado>(`/ocr/jobs/${jobId}`);
}

export function confirmarJob(
  jobId: number,
  items: { producto_id: number; cantidad: number }[],
): Promise<JobEstado> {
  return request<JobEstado>(`/ocr/jobs/${jobId}/confirmar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });
}
