export interface Zona {
  id: number;
  nombre: string;
  distrito: string;
  tiempo_estimado_min: number;
}

export interface Direccion {
  id: number;
  direccion_linea1: string;
  referencia: string | null;
  telefono_contacto: string;
  zona_id: number;
}

export interface DireccionInput {
  direccion_linea1: string;
  referencia?: string;
  telefono_contacto: string;
  zona_id: number;
}

export interface CheckoutPagoResponse {
  payment_intent_id: string;
  client_secret: string;
  monto: number;
  moneda: string;
  reserva_expira_en: string | null;
}

export interface PedidoResumen {
  numero: string;
  estado: string;
  monto: number;
  moneda: string;
}

export interface PagoEstado {
  estado: 'procesando' | 'confirmado' | 'rechazado' | string;
  pedido: PedidoResumen | null;
}

export interface PedidoItem {
  producto_id: number;
  nombre: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

export interface Pedido {
  numero: string;
  estado: string;
  items: PedidoItem[];
  monto: number;
  moneda: string;
  metodo_entrega: string;
  entrega: string;
}

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

export function getZonas(): Promise<Zona[]> {
  return request<Zona[]>('/zonas');
}

export function getDirecciones(): Promise<Direccion[]> {
  return request<Direccion[]>('/direcciones');
}

export function createDireccion(payload: DireccionInput): Promise<Direccion> {
  return request<Direccion>('/direcciones', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function iniciarCheckout(payload: {
  direccion_id?: number;
  metodo_entrega: 'delivery' | 'retiro';
}): Promise<CheckoutPagoResponse> {
  return request<CheckoutPagoResponse>('/checkout', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getPagoEstado(paymentIntentId: string): Promise<PagoEstado> {
  return request<PagoEstado>(`/pagos/${encodeURIComponent(paymentIntentId)}`);
}

export function getPedido(numero: string): Promise<Pedido> {
  return request<Pedido>(`/pedidos/${encodeURIComponent(numero)}`);
}
