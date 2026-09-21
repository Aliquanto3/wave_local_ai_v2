import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

// Not automatic without `test.globals: true` in vite.config.ts: without this,
// a component rendered by one test stays in the DOM for the next one in the
// same file.
afterEach(() => {
  cleanup()
})
