import type { Progress } from '../api/client'
import { kgToDisplay, weightUnit, type Units } from '../units'

/** Daily weigh-ins as dots, 7-day moving average as a line. */
export function TrendChart({ points, units }: { points: Progress['weights']; units: Units }) {
  if (points.length < 2) {
    return <div className="empty"><strong>Not enough data yet</strong>Log your weight on a few different days to see your trend.</div>
  }
  const W = 640, H = 220, pad = { l: 40, r: 12, t: 12, b: 28 }
  const xs = points.map((p) => new Date(p.date).getTime())
  const vals = points.flatMap((p) => [kgToDisplay(p.weight_kg, units), kgToDisplay(p.trend_kg, units)])
  const minY = Math.floor(Math.min(...vals) - 0.5), maxY = Math.ceil(Math.max(...vals) + 0.5)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const x = (t: number) => pad.l + ((t - minX) / Math.max(maxX - minX, 1)) * (W - pad.l - pad.r)
  const y = (v: number) => pad.t + (1 - (v - minY) / Math.max(maxY - minY, 1)) * (H - pad.t - pad.b)
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(xs[i]).toFixed(1)},${y(kgToDisplay(p.trend_kg, units)).toFixed(1)}`).join(' ')
  const ticks = [minY, (minY + maxY) / 2, maxY]
  const fmt = (t: number) => new Date(t).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`Weight trend in ${weightUnit(units)}`}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="var(--rule)" />
          <text x={pad.l - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--stone)">{t.toFixed(1)}</text>
        </g>
      ))}
      {points.map((p, i) => (
        <circle key={p.date} cx={x(xs[i])} cy={y(kgToDisplay(p.weight_kg, units))} r="3" fill="var(--stone)" opacity="0.45" />
      ))}
      <path d={line} fill="none" stroke="var(--avocado)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <text x={pad.l} y={H - 8} fontSize="11" fill="var(--stone)">{fmt(minX)}</text>
      <text x={W - pad.r} y={H - 8} fontSize="11" fill="var(--stone)" textAnchor="end">{fmt(maxX)}</text>
    </svg>
  )
}
