import { useEffect, useRef } from 'react'

/** A run's merged output, appended as it streams, kept scrolled to the end. */
export function LiveOutput({ lines }: { lines: string[] }) {
  const end = useRef<HTMLPreElement>(null)

  useEffect(() => {
    if (end.current !== null) {
      end.current.scrollTop = end.current.scrollHeight
    }
  }, [lines])

  return (
    <pre className="live-output" aria-label="Live output" ref={end}>
      {lines.map((line, index) => (
        <div key={index}>{line}</div>
      ))}
    </pre>
  )
}
