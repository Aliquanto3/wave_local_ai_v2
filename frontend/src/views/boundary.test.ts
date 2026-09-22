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

const overviewQualitySources = import.meta.glob('./overview/quality/**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

const overviewRuntimeSources = import.meta.glob('./overview/runtime/**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>

const overviewShellSources = import.meta.glob('./overview/*.{ts,tsx}', {
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

// The overview's own quality/runtime pair (see plan.md's Decisions on the
// view-boundary carve-out): `OverviewCard.tsx`/`OverviewView.tsx` are the
// only files allowed to know both `overview/quality` and `overview/runtime`
// exist, and only through their components -- never through a cross-import
// of the other's type module. Confirmed this fails before the fix: a
// cross-import (`import type { OverviewRuntimeView } from '../runtime/types'`)
// was temporarily added to `overview/quality/QualityPanel.tsx`, the test run
// to see it fail ("imports ../runtime/types"), and the line removed -- same
// proof method as the pairs above.
describe('the overview quality/runtime component boundary', () => {
  it('no file under overview/quality/ imports from overview/runtime/ or views/energy/', () => {
    for (const [path, text] of Object.entries(overviewQualitySources)) {
      const violation = importedModuleSpecifiers(text).find(
        (s) => s.includes('runtime') || s.includes('energy'),
      )
      expect(violation, `${path} imports ${String(violation)}`).toBeUndefined()
    }
  })

  it('no file under overview/runtime/ imports from overview/quality/', () => {
    for (const [path, text] of Object.entries(overviewRuntimeSources)) {
      const violation = importedModuleSpecifiers(text).find((s) =>
        s.includes('quality'),
      )
      expect(violation, `${path} imports ${String(violation)}`).toBeUndefined()
    }
  })

  it('no overview shell file imports the quality or runtime type modules', () => {
    for (const [path, text] of Object.entries(overviewShellSources)) {
      const violation = importedModuleSpecifiers(text).find(
        (s) => s.includes('quality/types') || s.includes('runtime/types'),
      )
      // OverviewView.tsx is the one file allowed to know the quality store's
      // shape (it derives the suite list and leader roster ids from it) --
      // never the runtime store's.
      if (path.endsWith('OverviewCard.tsx')) {
        expect(violation, `${path} imports ${String(violation)}`).toBeUndefined()
      } else {
        const runtimeTypesViolation = importedModuleSpecifiers(text).find((s) =>
          s.includes('runtime/types'),
        )
        expect(
          runtimeTypesViolation,
          `${path} imports ${String(runtimeTypesViolation)}`,
        ).toBeUndefined()
      }
    }
  })
})
