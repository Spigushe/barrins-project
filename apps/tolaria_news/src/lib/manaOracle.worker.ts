/**
 * Web Worker entry for the "Tolaria West" mana-source calculator.
 *
 * The sweep runs up to ~(100 land counts × 100 000 games × a handful of
 * 99-card shuffles), which would jank the main thread for seconds. Vite
 * bundles this into its own chunk because `useManaOracle` references it via
 * `new Worker(new URL('./manaOracle.worker.ts', import.meta.url), ...)`.
 */
import { runSimulation } from './manaOracle'
import type { OracleParams, OracleResponse } from './manaOracle'

/** Minimal view of the dedicated-worker global — declared locally so this
 * file needs no `webworker` lib reference (which would clash with the DOM
 * lib the rest of the app is compiled against). */
type WorkerScope = {
  postMessage: (message: OracleResponse) => void
  onmessage: ((event: MessageEvent<OracleParams>) => void) | null
}

const ctx = self as unknown as WorkerScope

ctx.onmessage = (event) => {
  const params = event.data
  try {
    const result = runSimulation(params, Math.random, (fraction) => {
      ctx.postMessage({ type: 'progress', fraction })
    })
    ctx.postMessage({ type: 'done', result })
  } catch (error) {
    ctx.postMessage({
      type: 'error',
      message: error instanceof Error ? error.message : 'Simulation failed.',
    })
  }
}
