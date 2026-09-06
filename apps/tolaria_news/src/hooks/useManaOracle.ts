import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  OracleNotFound,
  OracleParams,
  OracleResponse,
  OracleResult,
} from '@/lib/manaOracle'

type Status = 'idle' | 'running' | 'done' | 'error'

/**
 * Drives the mana-source simulation on a Web Worker so a large run never
 * freezes the tab. One worker per run; the previous one is terminated on
 * re-run and on unmount.
 */
export function useManaOracle() {
  const workerRef = useRef<Worker | null>(null)
  const [status, setStatus] = useState<Status>('idle')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<OracleResult | OracleNotFound | null>(null)
  const [error, setError] = useState<string | null>(null)

  const teardown = useCallback(() => {
    workerRef.current?.terminate()
    workerRef.current = null
  }, [])

  useEffect(() => teardown, [teardown])

  const run = useCallback(
    (params: OracleParams) => {
      teardown()
      setStatus('running')
      setProgress(0)
      setResult(null)
      setError(null)

      const worker = new Worker(new URL('../lib/manaOracle.worker.ts', import.meta.url), {
        type: 'module',
      })
      workerRef.current = worker

      worker.onmessage = (event: MessageEvent<OracleResponse>) => {
        const message = event.data
        if (message.type === 'progress') {
          setProgress(message.fraction)
          return
        }
        if (message.type === 'done') {
          setResult(message.result)
          setProgress(1)
          setStatus('done')
          teardown()
          return
        }
        setError(message.message)
        setStatus('error')
        teardown()
      }

      worker.onerror = () => {
        setError('The simulation worker crashed.')
        setStatus('error')
        teardown()
      }

      worker.postMessage(params)
    },
    [teardown],
  )

  const reset = useCallback(() => {
    teardown()
    setStatus('idle')
    setProgress(0)
    setResult(null)
    setError(null)
  }, [teardown])

  return { status, progress, result, error, run, reset }
}
