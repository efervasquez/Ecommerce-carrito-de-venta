export interface PedidoDespacho {
  numero: string;
  estado: string;
  zona_id: number;
  distrito: string;
  metodo_entrega: string;
  motorizado_id: number | null;
  monto: number;
  creado_en: string;
}

export interface ZonaDespachoResumen {
  zona_id: number;
  nombre: string;
  distrito: string;
  pedidos_registrados: number;
  pedidos_preparando: number;
  pedidos_en_camino: number;
  pedidos_entregados: number;
}

export interface AsignacionInput {
  zona_id: number;
  pedido_numeros: string[];
  motorizado_id: number;
}

export interface AsignacionResponse {
  zona_id: number;
  motorizado_id: number;
  asignados: string[];
}

export interface HistorialEstado {
  estado_anterior: string | null;
  estado_nuevo: string;
  usuario_id: number | null;
  timestamp: string;
}

export type EstadoPedidoManual = 'En camino' | 'Entregado';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

function headers(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...headers(), ...(init?.headers ?? {}) },
  });
  const body = (await response.json()) as T | { detail?: string };
  if (!response.ok) {
    const detail =
      body && typeof body === 'object' && 'detail' in body && body.detail
        ? String(body.detail)
        : 'No se pudo completar la solicitud.';
    throw new Error(detail);
  }
  return body as T;
}

export function getPedidos(params?: {
  estado?: string;
  zona_id?: number;
}): Promise<PedidoDespacho[]> {
  const search = new URLSearchParams();
  if (params?.estado) search.set('estado', params.estado);
  if (params?.zona_id) search.set('zona_id', String(params.zona_id));
  const query = search.toString();
  return request<PedidoDespacho[]>(`/despacho/pedidos${query ? `?${query}` : ''}`);
}

export function getZonasDespacho(): Promise<ZonaDespachoResumen[]> {
  return request<ZonaDespachoResumen[]>('/despacho/zonas');
}

export function asignarLote(payload: AsignacionInput): Promise<AsignacionResponse> {
  return request<AsignacionResponse>('/despacho/asignaciones', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPendientes(zonaId: number): Promise<PedidoDespacho[]> {
  return request<PedidoDespacho[]>(
    `/despacho/pedidos/pendientes?zona_id=${encodeURIComponent(zonaId)}`,
  );
}

export function getMisPedidos(): Promise<PedidoDespacho[]> {
  return request<PedidoDespacho[]>('/despacho/pedidos/mios');
}

export function autoAsignar(numero: string): Promise<PedidoDespacho> {
  return request<PedidoDespacho>(
    `/despacho/pedidos/${encodeURIComponent(numero)}/auto-asignar`,
    { method: 'POST' },
  );
}

export function cambiarEstado(
  numero: string,
  estado: EstadoPedidoManual,
): Promise<PedidoDespacho> {
  return request<PedidoDespacho>(
    `/despacho/pedidos/${encodeURIComponent(numero)}/estado`,
    { method: 'PATCH', body: JSON.stringify({ estado }) },
  );
}

export function getHistorial(numero: string): Promise<HistorialEstado[]> {
  return request<HistorialEstado[]>(
    `/despacho/pedidos/${encodeURIComponent(numero)}/historial`,
  );
}
