/**
 * Runtime configuration.
 *
 * Every environment-specific value is read here exactly once so no component
 * reaches into `import.meta.env` directly. Defaults keep `npm run dev` working
 * without a `.env` file; production values come from the environment.
 */

const DEFAULT_API_URL = 'http://localhost:8000';
const DEFAULT_WS_URL = 'ws://localhost:8000/ws/shuttles';
const DEFAULT_MAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';

export const env = {
  apiUrl: import.meta.env.VITE_API_URL ?? DEFAULT_API_URL,
  wsUrl: import.meta.env.VITE_WS_URL ?? DEFAULT_WS_URL,
  mapStyleUrl: import.meta.env.VITE_MAP_STYLE_URL ?? DEFAULT_MAP_STYLE_URL,
} as const;
