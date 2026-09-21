/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // The service's default bind (settings.DEFAULT_SERVICE_HOST/_PORT).
      '/api': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    coverage: {
      provider: 'v8',
      // Every source file counts, loaded by a test or not: without `include`,
      // deleting a test file drops its subject from the denominator and the
      // percentage goes up instead of failing the gate.
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/setupTests.ts',
        'src/views/fixtures/**',
        'src/main.tsx',
      ],
      thresholds: {
        lines: 80,
      },
    },
  },
})
