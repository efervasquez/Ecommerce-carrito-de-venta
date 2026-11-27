import React, { createContext, useContext, useEffect, useState } from 'react';

const StripeContext = createContext<any>(null);

export const Elements: React.FC<any> = ({ stripe, children }) => {
  const [instance, setInstance] = useState<any>(() =>
    stripe && typeof stripe.then !== 'function' ? stripe : null,
  );
  useEffect(() => {
    let vigente = true;
    Promise.resolve(stripe).then((value) => {
      if (vigente) setInstance(value);
    });
    return () => {
      vigente = false;
    };
  }, [stripe]);
  return <StripeContext.Provider value={instance}>{children}</StripeContext.Provider>;
};

export const CardElement: React.FC = () => (
  <div aria-label="Número de tarjeta" style={{ padding: '0.75rem', border: '1px solid #cbd5e1', borderRadius: 4 }}>
    Tarjeta (Stripe Elements)
  </div>
);

export const PaymentElement: React.FC = () => <CardElement />;

export function useStripe(): any {
  return useContext(StripeContext);
}

export function useElements(): any {
  return { getElement: () => ({}) };
}
