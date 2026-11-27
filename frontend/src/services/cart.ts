export interface CartItem {
  producto_id: number;
  nombre: string;
  imagen_url: string | null;
  cantidad: number;
  precio_regular: number;
  descuento_porcentaje: number;
  precio_final: number;
  subtotal: number;
  ahorro: number;
  stock_disponible: number;
}

export interface CartResponse {
  items_oferta: CartItem[];
  items_regulares: CartItem[];
  subtotal: number;
  ahorro_total: number;
  total: number;
  reserva_expira_en: string | null;
}

export interface CheckoutResponse {
  message: string;
  reserva_expira_en: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

function headers(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...init,
    headers: { ...headers(), ...(init?.headers ?? {}) },
  });
  const body = (await response.json()) as T | { detail?: string };
  if (!response.ok) {
    throw new Error(
      body && typeof body === 'object' && 'detail' in body && body.detail
        ? String(body.detail)
        : 'No se pudo actualizar el carrito.',
    );
  }
  return body as T;
}

export function getCart(): Promise<CartResponse> {
  return request<CartResponse>('/carrito');
}

export function addCartItem(productoId: number, cantidad: number): Promise<CartResponse> {
  return request<CartResponse>('/carrito/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ producto_id: productoId, cantidad }),
  });
}

export function updateCartItem(productoId: number, cantidad: number): Promise<CartResponse> {
  return request<CartResponse>(`/carrito/items/${productoId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cantidad }),
  });
}

export function deleteCartItem(productoId: number): Promise<CartResponse> {
  return request<CartResponse>(`/carrito/items/${productoId}`, { method: 'DELETE' });
}

export function checkoutCart(): Promise<CheckoutResponse> {
  return request<CheckoutResponse>('/checkout', { method: 'POST' });
}
