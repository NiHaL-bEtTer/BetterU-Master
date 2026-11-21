// BetterU dashboard pieces in the style of the Watermelon UI "Bionis" dashboard.
import { useId, type ComponentType, type ReactNode, type SVGProps } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartTooltip } from '@/components/watermelon/bionis-dashboard/components/bionis/shared'
import { CalendarIcon, TrendUpIcon, WarningFilledIcon } from '@/components/watermelon/bionis-dashboard/components/bionis/icons'
import { cn } from '@/lib/utils'

const ANIM = 900
const AXIS_TICK = { fill: 'var(--muted-foreground)', fontSize: 10, fontFamily: 'Geist, sans-serif' } as const

export type DayPoint = { date: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number }

/* ── Metric card ──────────────────────────────────────────────────────── */

export function MetricCard({ icon: Icon, color, label, value, unit, trendUp, emphasis, note, to }: {
  icon: ComponentType<SVGProps<SVGSVGElement>>; color: string; label: string; value: string; unit: string
  trendUp: boolean; emphasis: string; note: string; to?: string
}) {
  const body = (
    <>
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-md text-white" style={{ backgroundColor: color }}>
            <Icon className="size-3.5" />
          </span>
          <p className="truncate text-sm font-medium tracking-tight">{label}</p>
        </div>
        {to && <span className="text-xs text-muted-foreground transition-colors group-hover:text-foreground">Details</span>}
      </div>
      <div className="flex flex-col gap-3">
        <p className="leading-none">
          <span className="text-2.5xl font-medium tabular-nums">{value}</span> <span className="font-normal">{unit}</span>
        </p>
        <div className="flex items-center gap-2">
          <TrendUpIcon className={cn(trendUp ? 'text-(--trend)' : 'rotate-180 text-destructive')} />
          <p className="text-xs"><span className="font-medium">{emphasis}</span> <span className="text-muted-foreground">{note}</span></p>
        </div>
      </div>
    </>
  )
  const cls = 'group flex min-h-37.5 min-w-0 flex-col justify-between rounded-2xl border p-4 transition-shadow hover:shadow-[0_4px_18px_rgba(0,0,0,0.05)]'
  return to ? <Link to={to} className={cls}>{body}</Link> : <article className={cls}>{body}</article>
}

/* ── Card shell with Bionis header ────────────────────────────────────── */

export function ChartCard({ icon: Icon, color, title, badge, badgeTone = 'period', children, className }: {
  icon: ComponentType<SVGProps<SVGSVGElement>>; color: string; title: string; badge?: ReactNode
  badgeTone?: 'period' | 'warn'; children: ReactNode; className?: string
}) {
  return (
    <article className={cn('flex min-h-106.5 flex-col gap-6 rounded-2xl border bg-background p-4', className)}>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex items-center gap-3">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg text-white" style={{ backgroundColor: color }}>
            <Icon className="size-4.5" />
          </span>
          <h3 className="text-lg font-medium">{title}</h3>
        </div>
        {badge ? (
          badgeTone === 'warn' ? (
            <span className="inline-flex h-8 shrink-0 items-center gap-2 rounded-xl bg-(--chart-warn-bg) py-1 pr-4 pl-3 text-sm font-medium text-(--chart-warn)">
              <WarningFilledIcon className="size-5" />{badge}
            </span>
          ) : (
            <span className="inline-flex h-8 shrink-0 items-center rounded-xl bg-(--chart-period-bg) px-3 py-1 text-sm font-medium text-(--chart-period)">{badge}</span>
          )
        ) : null}
      </div>
      {children}
    </article>
  )
}

/* ── Calories per day ─────────────────────────────────────────────────── */

function KcalBar({ x = 0, y = 0, width = 0, height = 0, active = false, over = false }: { x?: number; y?: number; width?: number; height?: number; active?: boolean; over?: boolean }) {
  if (height <= 0) return null
  const cap = 3
  const color = over ? 'var(--chart-warn)' : 'var(--chart-sleep)'
  return (
    <g>
      {active && <rect x={x - 1} y={y - 1} width={width + 2} height={height + 1} rx={2} fill={color} opacity={0.12} />}
      <rect x={x} y={y + cap} width={width} height={Math.max(height - cap, 0)} fill={active ? color : over ? `color-mix(in srgb, ${color} 14%, transparent)` : 'color-mix(in srgb, var(--brand-leaf) 38%, transparent)'} opacity={active ? 0.28 : 1} />
      <rect x={x} y={y} width={width} height={cap} fill={color} />
    </g>
  )
}

export function CaloriesChart({ days, target }: { days: DayPoint[]; target: number }) {
  const data = days.map((d) => {
    const date = new Date(`${d.date}T12:00:00`)
    return {
      ...d,
      label: date.toLocaleDateString(undefined, days.length > 10 ? { day: 'numeric' } : { weekday: 'short' }).toUpperCase(),
      fullDate: date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' }),
      over: d.kcal > target * 1.05,
    }
  })
  const max = Math.max(target * 1.3, ...data.map((d) => d.kcal))
  const top = Math.ceil(max / 500) * 500
  const overDays = data.filter((d) => d.over).length
  return (
    <ChartCard icon={CalendarIcon} color="var(--metric-kcal)" title="Calories per day" badge={overDays ? `${overDays} ${overDays === 1 ? 'day' : 'days'} over target` : undefined} badgeTone="warn">
      <div className="h-82.5 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 8 }} barCategoryGap="18%">
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="4 4" />
            <XAxis dataKey="label" axisLine={false} tickLine={false} interval={days.length > 14 ? 2 : 0} tick={AXIS_TICK} height={28} />
            <YAxis domain={[0, top]} tickCount={6} axisLine={false} tickLine={false} tick={AXIS_TICK} width={42} tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`)} />
            <ReferenceLine y={target} stroke="var(--foreground)" strokeOpacity={0.45} strokeDasharray="5 5" label={{ value: `Target ${Math.round(target)}`, position: 'insideTopRight', fill: 'var(--muted-foreground)', fontSize: 10 }} />
            <Tooltip cursor={false} content={<ChartTooltip items={[
              { label: 'Calories', dataKey: 'kcal', formatValue: (v) => (typeof v === 'number' ? `${Math.round(v)} kcal` : '—'), color: 'var(--chart-sleep)' },
              { label: 'Protein', dataKey: 'protein_g', formatValue: (v) => (typeof v === 'number' ? `${Math.round(v)} g` : '—'), color: 'var(--metric-protein)' },
            ]} />} />
            <Bar dataKey="kcal" shape={(p: object) => <KcalBar {...p} over={(p as { payload?: { over?: boolean } }).payload?.over} />} activeBar={(p: object) => <KcalBar {...p} active over={(p as { payload?: { over?: boolean } }).payload?.over} />} isAnimationActive animationDuration={ANIM} animationEasing="ease-out" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  )
}

/* ── Protein and calories vs target ───────────────────────────────────── */

export function TargetTrendChart({ days, kcalTarget, proteinTarget, periodLabel }: { days: DayPoint[]; kcalTarget: number; proteinTarget: number; periodLabel: string }) {
  const id = useId().replace(/:/g, '')
  const step = Math.max(1, Math.round(days.length / 7))
  const data = days.map((d, i) => {
    const date = new Date(`${d.date}T12:00:00`)
    return {
      dateKey: d.date,
      label: date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      fullDate: date.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' }),
      showTick: i % step === 0 || i === days.length - 1,
      kcal: d.kcal ? Math.round((d.kcal / kcalTarget) * 100) : null,
      protein: d.kcal ? Math.round((d.protein_g / proteinTarget) * 100) : null,
    }
  })
  return (
    <ChartCard icon={TrendUpIcon} color="var(--chart-steps)" title="Hitting your targets" badge={periodLabel}>
      <div className="-mt-2 flex flex-wrap items-center justify-center gap-3.5 sm:justify-end">
        <div className="flex items-center gap-2 text-sm font-medium text-(--chart-axis)"><span className="size-2 rounded-full bg-(--chart-steps)" />Protein, % of target</div>
        <div className="flex items-center gap-2 text-sm font-medium text-(--chart-axis)"><span className="size-2 rounded-full bg-(--chart-recovery)" />Calories, % of target</div>
      </div>
      <div className="h-75 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 22, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`p-${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-steps)" stopOpacity={0.6} /><stop offset="60%" stopColor="var(--chart-steps)" stopOpacity={0} /></linearGradient>
              <linearGradient id={`k-${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--chart-recovery)" stopOpacity={0.5} /><stop offset="60%" stopColor="var(--chart-recovery)" stopOpacity={0} /></linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeDasharray="4 4" />
            <XAxis dataKey="dateKey" axisLine={false} tickLine={false} interval={0} tick={({ x, y, index }: { x?: number; y?: number; index?: number }) => {
              const p = typeof index === 'number' ? data[index] : undefined
              if (!p?.showTick || x == null || y == null) return <g />
              return <text x={x} y={y + 10} textAnchor="middle" fill="var(--muted-foreground)" fontSize={10} fontFamily="Geist, sans-serif">{p.label}</text>
            }} />
            <YAxis domain={[0, 140]} ticks={[0, 25, 50, 75, 100, 125]} axisLine={false} tickLine={false} tick={AXIS_TICK} width={36} tickFormatter={(v: number) => `${v}%`} />
            <ReferenceLine y={100} stroke="var(--foreground)" strokeOpacity={0.35} strokeDasharray="5 5" />
            <Tooltip cursor={{ stroke: 'var(--foreground)', strokeWidth: 1, strokeDasharray: '4 4', strokeOpacity: 0.35 }} content={<ChartTooltip icon={CalendarIcon} items={[
              { label: 'Protein', dataKey: 'protein', formatValue: (v) => (typeof v === 'number' ? `${v}%` : 'Not logged'), color: 'var(--chart-steps)' },
              { label: 'Calories', dataKey: 'kcal', formatValue: (v) => (typeof v === 'number' ? `${v}%` : 'Not logged'), color: 'var(--chart-recovery)' },
            ]} />} />
            <Area type="monotone" dataKey="protein" stroke="var(--chart-steps)" strokeWidth={2} fill={`url(#p-${id})`} connectNulls dot={false} activeDot={{ r: 4 }} isAnimationActive animationDuration={ANIM} />
            <Area type="monotone" dataKey="kcal" stroke="var(--chart-recovery)" strokeWidth={2} fill={`url(#k-${id})`} connectNulls dot={false} activeDot={{ r: 4 }} isAnimationActive animationDuration={ANIM} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  )
}

/* ── Insight card ─────────────────────────────────────────────────────── */

export function InsightCard({ icon: Icon, color, tint, title, badge, children }: {
  icon: ComponentType<SVGProps<SVGSVGElement>>; color: string; tint: string; title: string; badge?: string; children: ReactNode
}) {
  return (
    <article className="flex min-h-85.5 flex-col gap-6 rounded-2xl border p-4" style={{ background: `linear-gradient(180deg, ${tint} 0%, transparent 42%)` }}>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-md text-white" style={{ backgroundColor: color }}><Icon className="size-4" /></span>
          <h3 className="font-medium">{title}</h3>
        </div>
        {badge && <span className="inline-flex shrink-0 items-center rounded-xl bg-background px-2.5 py-2 text-xs font-medium tracking-tight text-(--chart-period)">{badge}</span>}
      </div>
      {children}
    </article>
  )
}
