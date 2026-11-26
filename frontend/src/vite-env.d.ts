/// <reference types="vite/client" />

declare module '@stripe/stripe-js' {
  export function loadStripe(publishableKey: string): Promise<any>;
}

declare module '@stripe/react-stripe-js' {
  import type * as React from 'react';
  export const Elements: React.ComponentType<any>;
  export const CardElement: React.ComponentType<any>;
  export const PaymentElement: React.ComponentType<any>;
  export function useStripe(): any;
  export function useElements(): any;
}
