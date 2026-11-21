import { lazy, Suspense, useEffect, useState, type ReactNode } from 'react'
import { round } from '../units'

const Silk = lazy(() => import('./rb/Silk/Silk'))

export function useWide(min = 1100) {
  const query = `(min-width: ${min}px)`
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const on = () => setWide(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [query])
  return wide
}

const still = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** Forest card with a slow silk background: the one animated surface per screen. */
export function HeroCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`hero-card ${className}`}>
      <div className="hero-card-bg" aria-hidden="true">
        <Suspense fallback={null}>
          <Silk color="#3d9a58" sheenColor="#e2fba6" speed={1.8} scale={1} rotation={0.4} sheen={1} depth={0.85} glow={0.6} noiseIntensity={0.7} clickRipple={false} paused={still()} />
        </Suspense>
      </div>
      <div className="hero-card-veil" aria-hidden="true" />
      <div className="hero-card-body">{children}</div>
    </section>
  )
}

/** Progress ring. `value / target`, with an over-target state. */
export function Ring({ value, target, size = 200, stroke = 14, children, track = 'rgba(243,247,238,0.14)', color = '#b9e06a' }: {
  value: number; target: number; size?: number; stroke?: number; children?: ReactNode; track?: string; color?: string
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = target > 0 ? Math.min(value / target, 1) : 0
  const over = target > 0 && value > target * 1.03
  return (
    <div className="kcal-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={over ? '#f3f7ee' : color} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
          transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ transition: 'stroke-dashoffset 900ms var(--ease)' }} />
      </svg>
      <div className="ring-glass" style={{ inset: stroke + 6 }} aria-hidden="true" />
      <div className="ring-center">{children}</div>
    </div>
  )
}

export function MacroMeter({ label, value, target }: { label: string; value: number; target: number }) {
  const pct = target > 0 ? Math.min(value / target, 1) : 0
  return (
    <div className="macro-meter">
      <div className="row between"><span>{label}</span><span className="num"><b>{round(value)}</b> / {round(target)} g</span></div>
      <div className="macro-track"><i style={{ width: `${pct * 100}%` }} /></div>
    </div>
  )
}

/** Seven slim bars, today highlighted, a dashed line at the target. */
export function WeekBars({ days, target }: { days: { date: string; kcal: number }[]; target: number }) {
  const max = Math.max(target * 1.2, ...days.map((d) => d.kcal), 1)
  const today = days.at(-1)?.date
  return (
    <div className="week-bars" role="img" aria-label="Calories eaten each day this week">
      <div className="week-target" style={{ bottom: `${(target / max) * 100}%` }}><span>{round(target)}</span></div>
      {days.map((d) => (
        <div key={d.date} className={`week-col${d.date === today ? ' today' : ''}`}>
          <div className="week-bar-wrap">
            <div className="week-bar" style={{ height: `${Math.max((d.kcal / max) * 100, d.kcal ? 3 : 0)}%` }} title={`${round(d.kcal)} kcal`} />
          </div>
          <span>{new Date(`${d.date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'narrow' })}</span>
        </div>
      ))}
    </div>
  )
}

export function Sparkline({ values, width = 240, height = 64 }: { values: number[]; width?: number; height?: number }) {
  if (values.length < 2) return null
  const min = Math.min(...values), max = Math.max(...values)
  const pad = 4
  const x = (i: number) => pad + (i / (values.length - 1)) * (width - pad * 2)
  const y = (v: number) => pad + (1 - (v - min) / Math.max(max - min, 0.1)) * (height - pad * 2)
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} aria-hidden="true" preserveAspectRatio="none">
      <path d={`${d} L${x(values.length - 1)},${height} L${x(0)},${height} Z`} fill="var(--flesh)" opacity="0.6" />
      <path d={d} fill="none" stroke="var(--avocado)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export function Card({ title, action, children, className = '' }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && <div className="card-head">{title && <h2>{title}</h2>}{action}</div>}
      {children}
    </section>
  )
}
