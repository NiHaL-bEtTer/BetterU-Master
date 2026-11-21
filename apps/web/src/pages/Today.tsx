// Today, laid out like the Watermelon UI "Bionis" dashboard, on BetterU's data.
import { useEffect, useMemo, useState, type ComponentType, type SVGProps } from 'react'
import { Drumstick, Droplets, Dumbbell, Flame, MessageCircle, Scale, UtensilsCrossed, Wheat } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, errorMessage, todayISO, unwrap, type DaySummary, type Progress, type WorkoutPlan } from '../api/client'
import { useAuth } from '../auth'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import {
  AlertDiamondIcon, AlertTriangleIcon, BlingFilledIcon, CalendarIcon, CheckCircleRegularIcon, HeartbeatFilledIcon, Sparkles3FilledIcon,
} from '@/components/watermelon/bionis-dashboard/components/bionis/icons'
import { ScoreDonut } from '@/components/watermelon/bionis-dashboard/components/bionis/shared'
import { cn } from '@/lib/utils'
import { CaloriesChart, InsightCard, MetricCard, TargetTrendChart, type DayPoint } from '@/shell/dashboard'
import { round } from '../units'

const PERIODS = [
  { value: 7, label: 'Last 7 days' },
  { value: 14, label: 'Last 14 days' },
  { value: 30, label: 'Last 30 days' },
] as const

type Tone = 'success' | 'warning' | 'danger'
const toneIcon: Record<Tone, ComponentType<SVGProps<SVGSVGElement>>> = { success: CheckCircleRegularIcon, warning: AlertTriangleIcon, danger: AlertDiamondIcon }
const toneClass: Record<Tone, string> = { success: 'text-(--vital-good)', warning: 'text-(--prediction-warn)', danger: 'text-(--prediction-danger)' }

function greeting(name?: string) {
  const h = new Date().getHours()
  const part = h < 12 ? 'Good Morning' : h < 18 ? 'Good Afternoon' : 'Good Evening'
  return name ? `${part} ${name}` : part
}

export function Today() {
  const { user } = useAuth()
  const [period, setPeriod] = useState<7 | 14 | 30>(7)
  const [day, setDay] = useState<DaySummary | null>(null)
  const [days, setDays] = useState<DayPoint[] | null>(null)
  const [plan, setPlan] = useState<WorkoutPlan | null | undefined>(undefined)
  const [progress, setProgress] = useState<Progress | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    unwrap(api.GET('/api/log/{day}', { params: { path: { day: todayISO() } } })).then(setDay).catch((e) => setError(errorMessage(e)))
    unwrap(api.GET('/api/workouts/plan')).then((p) => setPlan(p ?? null)).catch(() => setPlan(null))
    unwrap(api.GET('/api/progress')).then(setProgress).catch(() => {})
  }, [])
  useEffect(() => {
    unwrap(api.GET('/api/log/week', { params: { query: { end: todayISO(), days: period } } })).then(setDays).catch(() => setDays([]))
  }, [period])

  const t = day?.targets
  const eaten = day?.totals
  const periodLabel = PERIODS.find((p) => p.value === period)!.label

  const stats = useMemo(() => {
    if (!days || !t) return null
    const logged = days.filter((d) => d.kcal > 0)
    const avg = (k: keyof DayPoint) => (logged.length ? logged.reduce((s, d) => s + (d[k] as number), 0) / logged.length : 0)
    const dayScores = days.map((d) => (d.kcal > 0 ? Math.max(0, 100 - Math.abs(d.kcal / t.recommended_calories - 1) * 100) : 0))
    const score = Math.round(dayScores.reduce((a, b) => a + b, 0) / days.length)
    return { logged: logged.length, kcal: avg('kcal'), protein: avg('protein_g'), carbs: avg('carbs_g'), fat: avg('fat_g'), score }
  }, [days, t])

  const condition = !stats ? null
    : stats.score >= 80 ? { text: 'On track', cls: 'bg-(--live)/10 text-(--live)' }
    : stats.score >= 50 ? { text: 'Getting there', cls: 'bg-(--chart-warn-bg) text-(--chart-warn)' }
    : { text: 'Just getting started', cls: 'bg-(--chart-period-bg) text-(--chart-period)' }

  const hour = new Date().getHours()
  const nextMeal = hour < 11 ? 'breakfast' : hour < 15 ? 'lunch' : hour < 21 ? 'dinner' : 'snack'
  const weighedToday = progress?.weights.at(-1)?.date === todayISO()

  const reads: { id: string; tone: Tone; title: string; description: string }[] = []
  if (stats && t) {
    const pShare = stats.protein / t.macros.protein_g
    reads.push(stats.logged === 0
      ? { id: 'log', tone: 'warning', title: 'No meals logged yet', description: 'Log a few days and Alden can spot patterns in what you eat.' }
      : stats.logged / period < 0.5
        ? { id: 'log', tone: 'warning', title: 'Logging is patchy', description: `${stats.logged} of ${period} days logged. Daily logs make your trends and targets more accurate.` }
        : { id: 'log', tone: 'success', title: 'Consistent logging', description: `${stats.logged} of ${period} days logged. That's enough data to trust your trends.` })
    if (stats.logged) {
      reads.push(pShare < 0.8
        ? { id: 'protein', tone: 'danger', title: 'Protein is running low', description: `Averaging ${round(stats.protein)} g against a ${round(t.macros.protein_g)} g target on logged days.` }
        : { id: 'protein', tone: 'success', title: 'Protein on point', description: `Averaging ${round(stats.protein)} g a day, ${round(pShare * 100)}% of target.` })
    }
    const est = progress?.estimated_tdee
    reads.push(est
      ? { id: 'tdee', tone: 'success', title: 'Maintenance learned', description: `Your logs and weigh-ins put maintenance at about ${round(est)} kcal.` }
      : { id: 'tdee', tone: 'warning', title: 'Maintenance estimate pending', description: progress?.message ?? 'Keep logging food and weight for two weeks.' })
  }

  const actions = [
    eaten && eaten.kcal === 0
      ? { id: 'log', icon: UtensilsCrossed, title: `Log your ${nextMeal}`, description: 'Search a food or tell Alden what you ate.', to: `/app/log?meal=${nextMeal}` }
      : { id: 'log', icon: UtensilsCrossed, title: `Plan ${nextMeal}`, description: t && eaten ? `${round(Math.max(t.recommended_calories - eaten.kcal, 0))} kcal left today.` : 'See what fits your day.', to: `/app/alden?q=${encodeURIComponent(`What's a good ${nextMeal} with about ${t && eaten ? Math.max(Math.round(t.recommended_calories - eaten.kcal), 300) : 500} kcal?`)}` },
    !weighedToday && { id: 'weigh', icon: Scale, title: 'Weigh in', description: 'Keeps your weight trend and maintenance estimate current.', to: '/app/progress' },
    { id: 'train', icon: Dumbbell, title: plan ? 'Start a workout' : 'Build a training plan', description: plan ? plan.title : 'Made for your goal, schedule and equipment.', to: '/app/train' },
    { id: 'ask', icon: MessageCircle, title: 'Ask Alden', description: 'Exact nutrition answers, with sources.', to: '/app/alden' },
  ].filter(Boolean).slice(0, 4) as { id: string; icon: ComponentType<SVGProps<SVGSVGElement>>; title: string; description: string; to: string }[]

  const vitals = t ? [
    { label: 'Daily target', value: `${round(t.recommended_calories)} kcal`, tone: 'good' },
    { label: 'Maintenance', value: `${round(progress?.estimated_tdee ?? t.tdee)} kcal`, tone: 'neutral' },
    { label: 'Resting burn', value: `${round(t.bmr)} kcal`, tone: 'neutral' },
    { label: 'Protein target', value: `${round(t.macros.protein_g)} g`, tone: 'neutral' },
    { label: 'Weight trend', value: progress?.weights.length ? `${progress.weights.at(-1)!.trend_kg.toFixed(1)} kg` : 'Not logged', tone: progress?.weights.length ? 'neutral' : 'warn' },
    { label: 'BMI', value: `${t.bmi}`, tone: t.bmi >= 18.5 && t.bmi < 25 ? 'good' : 'warn' },
  ] : []

  return (
    <div className="flex flex-col gap-8">
      {error && <div className="alert alert-error">{error}</div>}

      <div className="flex items-center justify-between gap-3">
        <h1 className="min-w-0 truncate text-xl font-medium md:text-2xl">{greeting(user?.name)}</h1>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button type="button" variant="outline" className="h-10 shrink-0 gap-1 rounded-lg px-3.5 text-sm font-normal tracking-tight shadow-[0_2px_4px_rgba(0,0,0,0.05)]">
              <CalendarIcon /><span>{periodLabel}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="bionis-dashboard betteru min-w-40">
            <DropdownMenuRadioGroup value={String(period)} onValueChange={(v) => setPeriod(Number(v) as 7 | 14 | 30)}>
              {PERIODS.map((p) => (
                <DropdownMenuRadioItem key={p.value} value={String(p.value)} className="font-normal text-muted-foreground data-[state=checked]:font-medium data-[state=checked]:text-foreground">{p.label}</DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Overall */}
      <section className="flex items-center gap-6">
        <div className="flex min-h-28.5 flex-col justify-between gap-4">
          <h2 className="text-lg font-medium">Overall consistency</h2>
          <div className="flex flex-col gap-2">
            {condition && <span className={cn('inline-flex w-fit rounded-xl px-3 py-1 text-sm font-medium', condition.cls)}>{condition.text}</span>}
            <p className="max-w-md text-sm leading-[1.4] text-muted-foreground">
              {stats && t ? (
                stats.logged ? <>You logged <span className="font-medium text-foreground">{stats.logged} of {period} days</span>, averaging {round(stats.kcal)} kcal against a {round(t.recommended_calories)} kcal target.</>
                  : <>Nothing logged in the {periodLabel.toLowerCase()}. Log your meals and your score builds from how close each day lands to your target.</>
              ) : 'Loading your days…'}
            </p>
          </div>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <ScoreDonut value={stats?.score ?? 0} />
        </div>
      </section>

      {/* Key metrics */}
      <section className="flex flex-col gap-3.5">
        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-medium">Key metrics</h2>
          <p className="text-sm text-muted-foreground">Today so far, against your daily targets</p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {t && eaten && stats ? (
            <>
              <MetricCard icon={Flame} color="var(--metric-kcal)" label="Calories eaten" value={round(eaten.kcal)} unit="kcal" to="/app/log"
                trendUp={eaten.kcal <= t.recommended_calories} emphasis={`${round(Math.abs(t.recommended_calories - eaten.kcal))} kcal`} note={eaten.kcal <= t.recommended_calories ? 'left today' : 'over today'} />
              <MetricCard icon={Drumstick} color="var(--metric-protein)" label="Protein" value={round(eaten.protein_g)} unit="g" to="/app/log"
                trendUp={eaten.protein_g >= stats.protein * 0.5} emphasis={`${round((eaten.protein_g / t.macros.protein_g) * 100)}%`} note={`of ${round(t.macros.protein_g)} g goal`} />
              <MetricCard icon={Wheat} color="var(--metric-carbs)" label="Carbohydrate" value={round(eaten.carbs_g)} unit="g" to="/app/log"
                trendUp={eaten.carbs_g <= t.macros.carbs_g} emphasis={`${round((eaten.carbs_g / t.macros.carbs_g) * 100)}%`} note={`of ${round(t.macros.carbs_g)} g goal`} />
              <MetricCard icon={Droplets} color="var(--metric-fat)" label="Fat" value={round(eaten.fat_g)} unit="g" to="/app/log"
                trendUp={eaten.fat_g <= t.macros.fat_g} emphasis={`${round((eaten.fat_g / t.macros.fat_g) * 100)}%`} note={`of ${round(t.macros.fat_g)} g goal`} />
            </>
          ) : [0, 1, 2, 3].map((i) => <div key={i} className="skeleton min-h-37.5 rounded-2xl" />)}
        </div>
      </section>

      {/* Charts */}
      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {days && t ? (
          <>
            <CaloriesChart key={`kcal-${period}`} days={days} target={t.recommended_calories} />
            <TargetTrendChart key={`trend-${period}`} days={days} kcalTarget={t.recommended_calories} proteinTarget={t.macros.protein_g} periodLabel={periodLabel} />
          </>
        ) : [0, 1].map((i) => <div key={i} className="skeleton min-h-106.5 rounded-2xl" />)}
      </section>

      {/* Insights */}
      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <InsightCard icon={Sparkles3FilledIcon} color="var(--insight-prediction)" tint="color-mix(in srgb, var(--brand-leaf) 22%, transparent)" title="Alden's read" badge={periodLabel}>
          <div className="flex flex-1 flex-col gap-2">
            {reads.map((r) => {
              const Icon = toneIcon[r.tone]
              return (
                <div key={r.id} className="flex flex-1 items-center gap-3 rounded-xl bg-muted px-3 py-2">
                  <Icon className={cn('size-5 shrink-0', toneClass[r.tone])} />
                  <div className="flex min-w-0 flex-col gap-1.5">
                    <p className="text-sm font-medium">{r.title}</p>
                    <p className="text-xs text-muted-foreground">{r.description}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </InsightCard>

        <InsightCard icon={HeartbeatFilledIcon} color="var(--insight-vitals)" tint="color-mix(in srgb, var(--brand-forest) 7%, transparent)" title="Your numbers" badge={t ? (t.goal_applied === 'cut' ? 'Losing fat' : t.goal_applied === 'bulk' ? 'Building muscle' : 'Maintaining') : undefined}>
          <div className="flex flex-1 flex-col justify-between rounded-xl bg-background p-3">
            {vitals.map((v) => (
              <div key={v.label} className="flex items-center justify-between gap-3 py-1.5">
                <p className="text-muted-foreground">{v.label}</p>
                <p className={cn('shrink-0 font-semibold tabular-nums', v.tone === 'good' ? 'text-(--vital-good)' : v.tone === 'warn' ? 'text-(--chart-warn)' : 'text-foreground')}>{v.value}</p>
              </div>
            ))}
            {t?.warnings.length ? <p className="pt-2 text-xs text-(--chart-warn)">{t.warnings[0]}</p> : null}
          </div>
        </InsightCard>

        <InsightCard icon={BlingFilledIcon} color="var(--insight-actions)" tint="color-mix(in srgb, var(--brand-avocado) 12%, transparent)" title="Next steps">
          <div className="flex flex-1 flex-col justify-between gap-2">
            {actions.map((a) => (
              <Link key={a.id} to={a.to} className="flex items-start gap-3 rounded-xl bg-muted px-3 py-2 transition-colors hover:bg-accent">
                <a.icon className="size-5 shrink-0 text-foreground" />
                <div className="flex min-w-0 flex-col gap-1.5">
                  <p className="text-sm font-medium">{a.title}</p>
                  <p className="truncate text-xs text-muted-foreground/80">{a.description}</p>
                </div>
              </Link>
            ))}
          </div>
        </InsightCard>
      </section>
    </div>
  )
}
