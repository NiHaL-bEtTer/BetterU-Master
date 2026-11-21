import { Link } from 'react-router-dom'

/** BetterU mark: a single leaf, drawn in the accent colour. */
export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="currentColor" d="M18.5 3.5C9.4 3.5 4.5 8.6 4.5 14.5c0 1.9.5 3.5 1.3 4.9 2.1-4.5 5.8-7.8 10.4-9.5-3.8 2.4-6.6 5.8-8.3 10 1 .5 2.2.8 3.5.8 5.9 0 9.4-5.1 7.1-17.2z" />
    </svg>
  )
}

export function Brand({ to = '/' }: { to?: string }) {
  return (
    <Link className="brand" to={to}>
      <Logo /> BetterU
    </Link>
  )
}
