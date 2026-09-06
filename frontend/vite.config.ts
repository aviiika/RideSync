/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  // The project keeps one .env at the repository root, shared with the
  // backend. Without this, Vite would look only in frontend/ and silently
  // fall back to the defaults in src/config/env.ts.
  envDir: '..',
  // MapLibre ships its own web worker. Vite's dependency optimizer rewrites
  // the bundle in dev and the worker entry goes missing, which leaves the map
  // rendering a style but never requesting a tile.
  optimizeDeps: { exclude: ['maplibre-gl'] },
  server: {
    port: 5173,
  },
  test: {
    // The default 'forks' pool fails to spawn workers on this OneDrive-backed
    // Windows path; threads start reliably and run the same suite.
    pool: 'threads',
    // Files run one at a time. Running eleven jsdom environments concurrently
    // on this path produced worker-spawn failures and timeouts that looked
    // like test failures but were not. The suite is small; the wall-clock cost
    // is a few seconds and the results are trustworthy.
    fileParallelism: false,
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
