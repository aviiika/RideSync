import { configure } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';

/**
 * Testing Library waits one second by default before giving up on a `findBy`.
 *
 * On this OneDrive-backed Windows path, with eleven test files running in
 * parallel, a React Query fetch plus render can legitimately take longer than
 * that - which showed up as a test that passed alone and failed intermittently
 * in the full suite. The assertions were right; the deadline was wrong.
 */
configure({ asyncUtilTimeout: 5000 });
