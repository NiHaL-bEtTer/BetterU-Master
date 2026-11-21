import type { ReactNode } from 'react'
import { round } from '../units'

export interface FactsRow {
  label: ReactNode
  amount: ReactNode
  /** Share of the daily target, 0–1+. Omit for rows without a target. */
  share?: number | null
  sub?: boolean
}

interface FactsProps {
  title?: string
  subtitle?: ReactNode
  heroLabel: ReactNode
  heroValue: ReactNode
  rows: FactsRow[]
  /** Column heading over the percentages. */
  shareHeading?: string
  foot?: ReactNode
  children?: ReactNode
  className?: string
}

/** The BetterU signature: a Nutrition Facts panel, used on the website and in the app. */
export function Facts({ title = 'Nutrition Facts', subtitle, heroLabel, heroValue, rows, shareHeading = '% of your target', foot, children, className = '' }: FactsProps) {
  return (
    <section className={`facts ${className}`} aria-label={title}>
      <div className="facts-title">{title}</div>
      {subtitle && <div className="facts-sub">{subtitle}</div>}
      <div className="facts-bar" />
      <div className="facts-hero">
        <span className="label">{heroLabel}</span>
        <span className="value">{heroValue}</span>
      </div>
      <div className="facts-bar mid" />
      {rows.some((r) => r.share != null) && <div className="facts-head">{shareHeading}</div>}
      {rows.map((r, i) => (
        <div key={i} className={`facts-row${r.sub ? ' sub' : ''}`}>
          <span><b>{r.label}</b> {r.amount}</span>
          <span className="pct">{r.share != null ? `${round(r.share * 100)}%` : ''}</span>
          {r.share != null && (
            <span className="facts-meter" aria-hidden="true">
              <i className={r.share > 1.05 ? 'over' : ''} style={{ width: `${Math.min(r.share, 1) * 100}%` }} />
            </span>
          )}
        </div>
      ))}
      {children}
      {foot && <div className="facts-foot">{foot}</div>}
    </section>
  )
}
