import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./frontend/tests/setup.ts'],
    include: ['frontend/tests/**/*.{test,spec}.{ts,tsx}', 'frontend/src/**/*.{test,spec}.{ts,tsx}'],
  },
});
