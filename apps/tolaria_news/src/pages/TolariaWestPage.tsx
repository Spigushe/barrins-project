import { useState, type FormEvent } from 'react'
import { z } from 'zod'
import { Card, CardTitle } from '@/components/ui/card'
import { Eyebrow } from '@/components/ui/eyebrow'
import { Button } from '@/components/ui/button'
import { manaValue } from '@/lib/manaOracle'
import { useManaOracle } from '@/hooks/useManaOracle'

const inputClass =
  'h-9 rounded-(--radius-input) border border-border bg-input px-2 text-sm text-foreground'

const formSchema = z.object({
  lands: z.coerce
    .number()
    .int('Whole number of lands, please')
    .min(1, 'At least one land')
    .max(99, 'A 99-card deck holds at most 99 lands'),
  colority: z
    .string()
    .trim()
    .min(1, 'Enter a colority, e.g. 1CC')
    .regex(/^[0-9cC]+$/, 'Use only digits and the letter C')
    .transform((value) => value.toUpperCase())
    .refine((value) => manaValue(value) >= 1, 'That would cost nothing to cast')
    .refine((value) => manaValue(value) <= 20, 'Keep the mana value at 20 or below'),
  simulations: z.coerce
    .number()
    .int('Whole number of simulations, please')
    .min(1, 'Run at least one simulation')
    .max(100_000, 'Cap is 100,000 simulations'),
})

type FormValues = z.infer<typeof formSchema>

type FieldErrors = Partial<Record<keyof FormValues, string>>

/**
 * "Tolaria West" easter egg — a client-side Monte Carlo mana-source
 * calculator, reachable only via {@link useSecretUnlock} triggers (never a
 * nav link). See `src/lib/manaOracle.ts` for the model and the §4.1 note.
 */
export function TolariaWestPage() {
  const [lands, setLands] = useState('39')
  const [colority, setColority] = useState('1CC')
  const [simulations, setSimulations] = useState('5000')
  const [errors, setErrors] = useState<FieldErrors>({})
  const oracle = useManaOracle()

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const parsed = formSchema.safeParse({ lands, colority, simulations })
    if (!parsed.success) {
      const next: FieldErrors = {}
      for (const issue of parsed.error.issues) {
        const key = issue.path[0]
        if (typeof key === 'string' && !(key in next)) {
          next[key as keyof FormValues] = issue.message
        }
      }
      setErrors(next)
      return
    }
    setErrors({})
    oracle.run(parsed.data)
  }

  const progressPercent = Math.round(oracle.progress * 100)

  return (
    <div className="flex max-w-[720px] flex-col gap-4">
      <Eyebrow>Tolaria West</Eyebrow>
      <CardTitle>How many sources to cast a spell?</CardTitle>

      <Card className="flex flex-col gap-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
              How many lands are in your deck?
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={99}
                className={inputClass}
                value={lands}
                onChange={(event) => setLands(event.target.value)}
              />
              {errors.lands && (
                <span className="font-normal text-destructive">{errors.lands}</span>
              )}
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
              What is the colority of the spell?
              <input
                type="text"
                className={inputClass}
                value={colority}
                onChange={(event) => setColority(event.target.value)}
              />
              {errors.colority && (
                <span className="font-normal text-destructive">{errors.colority}</span>
              )}
            </label>

            <label className="flex flex-col gap-1 text-xs font-semibold text-muted-foreground">
              Number of simulations
              <input
                type="number"
                inputMode="numeric"
                min={1}
                max={100_000}
                className={inputClass}
                value={simulations}
                onChange={(event) => setSimulations(event.target.value)}
              />
              {errors.simulations && (
                <span className="font-normal text-destructive">{errors.simulations}</span>
              )}
            </label>
          </div>

          <p className="text-[12.5px] leading-relaxed text-muted-foreground">
            Digits are generic mana; each <strong>C</strong> is one pip of the colour you
            need. So <strong>1CC</strong> is a three-mana spell that wants two coloured
            sources by turn three.
          </p>

          <Button type="submit" className="w-fit" disabled={oracle.status === 'running'}>
            {oracle.status === 'running' ? 'Shuffling…' : 'Find the sources'}
          </Button>
        </form>

        <p className="text-[12.5px] leading-relaxed text-muted-foreground">
          A Monte Carlo estimate over a limited number of iterations. The answer is the
          smallest source count whose success rate clears 90% at the <em>lower</em> bound
          of its confidence interval.
        </p>
      </Card>

      <div aria-live="polite" className="flex flex-col gap-4">
        {oracle.status === 'running' && (
          <Card role="status" className="text-[15px] text-muted-foreground">
            Simulating… {progressPercent}%
          </Card>
        )}

        {oracle.status === 'error' && (
          <Card className="border-destructive/40 text-[15px] text-destructive">
            {oracle.error ?? 'The simulation failed.'}
          </Card>
        )}

        {oracle.status === 'done' && oracle.result && (
          <OracleOutcome result={oracle.result} />
        )}
      </div>
    </div>
  )
}

function OracleOutcome({
  result,
}: {
  result: NonNullable<ReturnType<typeof useManaOracle>['result']>
}) {
  if (!result.found) {
    return (
      <Card className="flex flex-col gap-3 text-[15px] leading-relaxed text-muted-foreground">
        <p>
          {result.everyGameDiscarded
            ? `Every simulated game missed its land drops before turn ${String(result.targetTurn)} — raise the land count or lower the cost.`
            : `Couldn't reach 90% confidence for any number of sources, even at ${String(result.maxGoodLandsTried)}. Try more lands or a cheaper spell.`}
        </p>
        <WilsonNote />
      </Card>
    )
  }

  const discardedPercent = ((result.discardedGames / result.simulations) * 100).toFixed(2)

  return (
    <Card className="flex flex-col gap-3 text-[15px] leading-relaxed text-muted-foreground">
      <p>
        You need at least{' '}
        <strong className="text-foreground">{result.goodLands} lands</strong> producing
        the required colour to cast a{' '}
        <strong className="text-foreground">{result.colority}</strong> spell by turn{' '}
        <strong className="text-foreground">{result.targetTurn}</strong>. That is a{' '}
        <strong className="text-foreground">
          {(result.successRate * 100).toFixed(2)} ±{' '}
          {(result.ciHalfWidth * 100).toFixed(2)}%
        </strong>{' '}
        chance of success.
      </p>
      <p>
        {result.discardedGames} of {result.simulations} games ({discardedPercent}%) were
        discarded for not making land drops by turn {result.targetTurn}.
      </p>
      <WilsonNote />
    </Card>
  )
}

function WilsonNote() {
  return (
    <p className="text-[12.5px] italic">
      The confidence interval uses the{' '}
      <a
        href="https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval"
        target="_blank"
        rel="noreferrer"
        className="text-accent underline-offset-4 hover:underline"
      >
        Wilson score interval
      </a>
      .
    </p>
  )
}
