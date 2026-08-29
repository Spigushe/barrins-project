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
