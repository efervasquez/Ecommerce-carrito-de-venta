/// <reference types="vitest" />
import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Puente local a Stripe.js (cargado desde js.stripe.com). Evita depender de
    // paquetes npm no instalados y mantiene el mismo contrato de importacion.
    alias: {
      '@stripe/stripe-js': fileURLToPath(
        new URL('./src/stripe-stubs/stripe-js.ts', import.meta.url),
      ),
      '@stripe/react-stripe-js': fileURLToPath(
        new URL('./src/stripe-stubs/react-stripe-js.tsx', import.meta.url),
      ),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
  },
});
