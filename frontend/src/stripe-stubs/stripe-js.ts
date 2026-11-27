/* Puente local a Stripe.js cargado desde js.stripe.com (CSP ya autorizado).
 * El build usa estos archivos via alias en vite.config.ts; Vitest sustituye
 * los modulos @stripe/* por sus mocks virtuales. */
export interface StripeLike {
  confirmPayment: (...args: any[]) => Promise<any>;
  confirmCardPayment: (...args: any[]) => Promise<any>;
  createPaymentMethod: (...args: any[]) => Promise<any>;
  elements: (...args: any[]) => any;
}

declare global {
  interface Window {
    Stripe?: (publishableKey: string) => StripeLike;
  }
}

export function loadStripe(publishableKey: string): Promise<StripeLike | null> {
  const arnés = (globalThis as any).__hu07Stripe as StripeLike | undefined;
  if (arnés) {
    return Promise.resolve(arnés);
  }
  if (typeof window === 'undefined' || !window.Stripe) {
    return Promise.resolve(null);
  }
  return Promise.resolve(window.Stripe(publishableKey));
}
