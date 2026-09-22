// The structural quality/runtime component-boundary test (see plan.md's
// Decisions): a Vitest test reading each view directory's source text for
// the other view's type-module import path, rather than an ESLint rule --
// no import-boundary plugin is installed, and this is one rule.
//
// `import.meta.glob` (a Vite feature, not Node's `fs`) keeps this file
// within the app's own browser-only tsconfig, matching every other file
// under `src`.
//
// To confirm this test actually fails when the boundary is crossed, a
// cross-import was temporarily added to `views/quality/QualityView.tsx`
// (`import type { RuntimeView } from '../runtime/types'`), the test run to
// see it fail (it did -- "imports ../runtime/types"), and the line removed.

import { describe, expect, it } from 'vitest'

const qualitySources = import.meta.glob('./quality/**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

const runtimeSources = import.meta.glob('./runtime/**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

const comparisonSources = import.meta.glob('./comparison/**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

/**
 * Every `import ... from '...'` module specifier in `text`, ignoring
 * comments -- so a docstring that merely *names* the other view's path
 * (as this file's own header does) does not trip the scan.
 */
function importedModuleSpecifiers(text: string): string[] {
  const withoutComments = text
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
  const specifiers: string[] = []
  const importRegex = /from\s+['"]([^'"]+)['"]/g
  let match: RegExpExecArray | null
  while ((match = importRegex.exec(withoutComments)) !== null) {
    specifiers.push(match[1])
  }
  return specifiers
}

describe('the quality/runtime component boundary', () => {
  it('no file under views/quality/ imports from views/runtime/', () => {
    for (const [path, text] of Object.entries(qualitySources)) {
      const violation = importedModuleSpecifiers(text).find((s) =>
        s.includes('runtime'),
      )
      expect(violation, `${path} imports ${String(violation)}`).toBeUndefined()
    }
  })

  it('no file under views/runtime/ imports from views/quality/', () => {
    for (const [path, text] of Object.entries(runtimeSources)) {
      const violation = importedModuleSpecifiers(text).find((s) =>
        s.includes('quality'),
      )
      expect(violation, `${path} imports ${String(violation)}`).toBeUndefined()
    }
  })

  // Confirmed this fails before the fix: a cross-import
  // (`import type { RuntimeView } from '../runtime/types'`) was temporarily
  // added to `views/comparison/ComparisonView.tsx`, the test run to see it
  // fail ("imports ../runtime/types"), and the line removed -- same proof
  // method as the original pair above.
  // `energy` too: the energy screen renders runtime-store data, which the
  // quality-only comparison must not reach either.
  it('no file under views/comparison/ imports from views/runtime/ or views/energy/', () => {
    for (const [path, text] of Object.entries(comparisonSources)) {
      const violation = importedModuleSpecifiers(text).find(
        (s) => s.includes('runtime') || s.includes('energy'),
      )
      expect(violation, `${path} imports ${String(violation)}`).toBeUndefined()
    }
  })
})
