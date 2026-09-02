import type { SVGProps } from 'react'

const base: SVGProps<SVGSVGElement> = {
  viewBox: '0 0 24 24',
  fill: 'none',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

/** Barrin's Identity wordmark mark — a shield with a keyed centre. */
export function ShieldMark(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={30} height={30} {...base} strokeWidth={1.6} {...props}>
      <path d="M12 2.5 20 7v6c0 4.6-3.2 7.2-8 8.5C7.2 20.2 4 17.6 4 13V7z" />
      <circle cx={12} cy={10.5} r={2.4} />
      <path d="M12 12.9v3.4" />
    </svg>
  )
}

export function AlertIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={15} height={15} {...base} strokeWidth={2} {...props}>
      <circle cx={12} cy={12} r={9} />
      <path d="M12 8v5" />
      <path d="M12 16h.01" />
    </svg>
  )
}

export function Spinner(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={16} height={16} {...base} strokeWidth={2.4} {...props}>
      <path d="M12 3a9 9 0 1 0 9 9" />
      <circle cx={12} cy={12} r={9} opacity={0.2} />
    </svg>
  )
}

/** A met password rule. */
export function CheckIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={13} height={13} {...base} strokeWidth={2.6} {...props}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

/** An unmet password rule. */
export function DotIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={13} height={13} {...base} strokeWidth={2} {...props}>
      <circle cx={12} cy={12} r={3.5} />
    </svg>
  )
}

export function MailIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={15} height={15} {...base} {...props}>
      <rect x={3} y={5} width={18} height={14} rx={2} />
      <path d="m3 7 9 6 9-6" />
    </svg>
  )
}

/** Password-reset marker — a key. */
export function KeyIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={15} height={15} {...base} {...props}>
      <circle cx={8.5} cy={14.5} r={4.5} />
      <path d="M11.7 11.3 20 3" />
      <path d="m16.5 6.5 2.5 2.5" />
      <path d="m13.5 9.5 2 2" />
    </svg>
  )
}

/** Copy-to-clipboard affordance (service-account credentials). */
export function CopyIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={15} height={15} {...base} {...props}>
      <rect x={9} y={9} width={11} height={11} rx={2} />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

/** Small dismiss "x" — removing a scope chip from the create form. */
export function CloseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg width={12} height={12} {...base} strokeWidth={2.4} {...props}>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  )
}
