import { CheckIcon, DotIcon } from './icons'
import { PASSWORD_RULES } from './passwordPolicy'

/**
 * The live password-complexity checklist shared by the signup and
 * password-reset screens. Purely visual feedback — it never blocks a submit.
 */
export function PasswordRules({ value }: { value: string }) {
  return (
    <ul className="gg-rules">
      {PASSWORD_RULES.map((rule) => {
        const met = rule.test(value)
        return (
          <li key={rule.label} className="gg-rule" data-met={met}>
            {met ? <CheckIcon /> : <DotIcon />}
            <span>{rule.label}</span>
          </li>
        )
      })}
    </ul>
  )
}
