export interface Reclamo {
  id: number;
  pedido_origen_numero: string;
  pedido_reposicion_numero: string | null;
  pedido_reposicion_estado: string | null;
  producto_id: number;
  motivo: string;
  descripcion: string | null;
  estado: string;
  intentos_adicionales_realizados: number;
  intentos_restantes: number;
  foto_producto_url: string;
  foto_comprobante_url: string;
  comprobante_verificado: boolean | null;
  pertenencia_botica_verificada: boolean | null;
  defecto_fisico_verificado: boolean | null;
  motivo_falla: string | null;
  observaciones: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface ReclamoListado {
  id: number;
  pedido_origen_numero: string;
  pedido_reposicion_numero: string;
  producto_id: number;
  estado: string;
  intentos_adicionales_realizados: number;
  creado_en: string;
}

export interface ReclamoRegistro {
  id: number;
  pedido_origen_numero: string;
  pedido_reposicion_numero: string;
  producto_id: number;
  estado: string;
  intentos_adicionales_realizados: number;
  creado_en: string;
}

export interface InspeccionInput {
  resultado: 'conforme' | 'falla';
  comprobante_verificado: boolean;
  pertenencia_botica_verificada: boolean;
  defecto_fisico_verificado: boolean;
  motivo_falla?: string;
  observaciones?: string;
}

export interface InspeccionResponse {
  id: number;
  estado: string;
  intentos_adicionales_realizados?: number;
  intentos_restantes?: number;
  mensaje: string;
}

export interface PedidoItemOpcion {
  producto_id: number;
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

export interface PedidoDetalle {
  numero: string;
  estado: string;
  items: PedidoItemOpcion[];
  monto: number;
  moneda: string;
  metodo_entrega: string;
  entrega: string;
}

export interface NuevoReclamoInput {
  pedido_numero: string;
  producto_id: number;
  motivo: string;
  descripcion?: string;
  foto_producto: File;
  foto_comprobante: File;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

function authHeaders(json = true): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function parse<T>(response: Response): Promise<T> {
  const texto = await response.text();
  let body: unknown = null;
  if (texto) {
    try {
      body = JSON.parse(texto);
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    const detalle =
      body && typeof body === 'object' && 'detail' in body
        ? String((body as { detail: unknown }).detail)
        : 'No se pudo completar la solicitud.';
    throw new Error(detalle);
  }
  return body as T;
}

function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
  }).then((response) => parse<T>(response));
}

export function crearReclamo(payload: NuevoReclamoInput): Promise<ReclamoRegistro> {
  const form = new FormData();
  form.append('pedido_numero', payload.pedido_numero);
  form.append('producto_id', String(payload.producto_id));
  form.append('motivo', payload.motivo);
  if (payload.descripcion) {
    form.append('descripcion', payload.descripcion);
  }
  form.append('foto_producto', payload.foto_producto);
  form.append('foto_comprobante', payload.foto_comprobante);
  return fetch(`${API_BASE_URL}/reclamos`, {
    method: 'POST',
    headers: authHeaders(false),
    body: form,
  }).then((response) => parse<ReclamoRegistro>(response));
}

export function getReclamos(params?: {
  estado?: string;
  pedido_numero?: string;
}): Promise<ReclamoListado[]> {
  const search = new URLSearchParams();
  if (params?.estado) search.set('estado', params.estado);
  if (params?.pedido_numero) search.set('pedido_numero', params.pedido_numero);
  const query = search.toString();
  return jsonRequest<ReclamoListado[]>(`/reclamos${query ? `?${query}` : ''}`);
}

export function getPedido(numero: string): Promise<PedidoDetalle> {
  return jsonRequest<PedidoDetalle>(`/pedidos/${encodeURIComponent(numero)}`);
}

export function getReclamo(id: number): Promise<Reclamo> {
  return jsonRequest<Reclamo>(`/reclamos/${id}`);
}

export function registrarInspeccion(
  id: number,
  payload: InspeccionInput,
): Promise<InspeccionResponse> {
  return jsonRequest<InspeccionResponse>(`/reclamos/${id}/inspeccion-campo`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function solicitarReembolso(id: number): Promise<void> {
  return jsonRequest<void>(`/reclamos/${id}/reembolso`, {
    method: 'POST',
    body: JSON.stringify({ accion: 'reembolso' }),
  });
}

export const ESTADOS_RECLAMO = [
  'aprobado',
  'reintento_pendiente',
  'cerrado_exitoso',
  'escalado_supervision',
] as const;
