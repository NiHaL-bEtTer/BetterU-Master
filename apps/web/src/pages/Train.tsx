import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, errorMessage, unwrap, type PlanExercise, type WorkoutPlan, type WorkoutSet } from '../api/client'
import { HeroCard } from '../components/Dash'
import RubberSegment from '../components/rb/RubberSegment/RubberSegment'
import { useToast } from '../components/Toast'
import { displayToKg, kgToDisplay, weightUnit, type Units } from '../units'

const IDEAS = ['Full body, 45 minutes', 'Upper/lower split', 'Home workouts, dumbbells only', 'Build strength for running']

export function Train() {
  const [params, setParams] = useSearchParams()
  const [plan, setPlan] = useState<WorkoutPlan | null | undefined>(undefined)
  const [request, setRequest] = useState(params.get('request') ?? '')
  const [building, setBuilding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dayIdx, setDayIdx] = useState(0)
  const [todaySets, setTodaySets] = useState<WorkoutSet[]>([])
  const [showBuilder, setShowBuilder] = useState(!!params.get('request'))
  const [rest, setRest] = useState<number | null>(null)
  const [units, setUnits] = useState<Units>('metric')

  useEffect(() => {
    unwrap(api.GET('/api/workouts/plan')).then((p) => setPlan(p ?? null)).catch(() => setPlan(null))
    unwrap(api.GET('/api/workouts/sets/today')).then(setTodaySets).catch(() => {})
    api.GET('/api/profile').then(({ data }) => data && setUnits(data.profile.units as Units))
  }, [])

  useEffect(() => {
    if (rest === null) return
    if (rest <= 0) {
      navigator.vibrate?.(200)
      setRest(null)
      return
    }
    const t = window.setTimeout(() => setRest((r) => (r === null ? null : r - 1)), 1000)
    return () => window.clearTimeout(t)
  }, [rest])

  async function build() {
    setBuilding(true)
    setError(null)
    try {
      const p = await unwrap(api.POST('/api/workouts/plan', { body: { request } }))
      setPlan(p)
      setDayIdx(0)
      setShowBuilder(false)
      setParams({}, { replace: true })
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBuilding(false)
    }
  }

  const day = plan?.days[dayIdx]

  return (
    <div className="page">
      {plan ? (
        <HeroCard>
          <div className="train-hero">
            <div className="stack" style={{ gap: 10 }}>
              <p className="muted small">Your plan, {plan.days.length} days a week</p>
              <h1 className="hero-title">{plan.title}</h1>
              {plan.description && <p className="muted" style={{ maxWidth: '40em' }}>{plan.description}</p>}
            </div>
            <div className="train-hero-stats">
              <div><strong className="num">{todaySets.length}</strong><span>sets today</span></div>
              <div><strong className="num">{plan.days.reduce((n, d) => n + d.exercises.length, 0)}</strong><span>exercises</span></div>
              {!showBuilder && <button className="btn btn-leaf btn-sm" onClick={() => setShowBuilder(true)}>New plan</button>}
            </div>
          </div>
        </HeroCard>
      ) : null}

      {(showBuilder || plan === null) && (
        <HeroCard>
          <div className="builder">
            <div className="stack" style={{ gap: 10 }}>
              <h1 className="hero-title">{plan ? 'Build a new plan' : 'Your training plan starts here.'}</h1>
              <p className="muted" style={{ maxWidth: '38em' }}>BetterU uses your goal, training days and equipment, then picks from 876 exercises. Add anything specific, like time limits or injuries.</p>
            </div>
            <textarea className="builder-input" placeholder="e.g. Upper/lower split, 45 minutes max, go easy on my lower back"
              value={request} maxLength={1000} onChange={(e) => setRequest(e.target.value)} aria-label="What you want from your plan" />
            <div className="prompt-chips">
              {IDEAS.map((i) => <button key={i} type="button" className="builder-chip" onClick={() => setRequest(i)}>{i}</button>)}
            </div>
            {error && <div className="alert alert-error">{error}</div>}
            <div className="row">
              <button className="btn btn-leaf" disabled={building} onClick={build}>{building ? 'Building your plan, about 10 seconds' : 'Build my plan'}</button>
              {plan && <button className="btn btn-sm" style={{ color: 'var(--on-forest)' }} onClick={() => setShowBuilder(false)}>Cancel</button>}
            </div>
          </div>
        </HeroCard>
      )}

      {plan === undefined && <div className="skeleton" style={{ height: 200 }} />}

      {plan && day && (
        <>
          <div className="row between wrap" style={{ gap: 16 }}>
          <RubberSegment
            aria-label="Training day"
            items={plan.days.map((d, i) => ({ value: String(i), label: d.day }))}
            value={String(dayIdx)}
            onChange={(v) => setDayIdx(Number(v))}
            trackColor="var(--wash)"
            thumbColor="var(--forest)"
            textColor="var(--stone)"
            activeTextColor="var(--on-forest)"
            size="sm"
          />
          <h2 style={{ fontSize: 22 }}>{day.focus}</h2>
          </div>
          <div className="ex-grid">
          {day.exercises.map((ex) => (
            <ExerciseCard key={`${dayIdx}-${ex.exercise_id}`} ex={ex} planId={plan.id} units={units}
              doneToday={todaySets.filter((s) => s.exercise_id === ex.exercise_id)}
              onLogged={(s) => { setTodaySets((xs) => [...xs, s]); setRest(ex.rest_sec) }} />
          ))}
          </div>
        </>
      )}

      {rest !== null && (
        <div className="timer" role="timer" aria-live="polite">
          Rest {Math.floor(rest / 60)}:{String(rest % 60).padStart(2, '0')}
          <button className="btn btn-sm" onClick={() => setRest(null)}>Skip</button>
        </div>
      )}
    </div>
  )
}

function ExerciseCard({ ex, planId, units, doneToday, onLogged }: { ex: PlanExercise; planId: number; units: Units; doneToday: WorkoutSet[]; onLogged: (s: WorkoutSet) => void }) {
  const [last, setLast] = useState<WorkoutSet[]>([])
  const [open, setOpen] = useState(false)
  const [reps, setReps] = useState(() => Number(String(ex.reps).split('-').pop()) || 10)
  const [weight, setWeight] = useState(0)
  const [busy, setBusy] = useState(false)
  const toast = useToast()

  useEffect(() => {
    if (!open) return
    unwrap(api.GET('/api/workouts/exercises/{exercise_id}/last', { params: { path: { exercise_id: ex.exercise_id } } }))
      .then((sets) => { setLast(sets); if (sets[0]) { setWeight(Number(kgToDisplay(sets[0].weight_kg, units).toFixed(1))); setReps(sets[0].reps) } })
      .catch(() => {})
  }, [open, ex.exercise_id, units])

  async function logSet() {
    setBusy(true)
    try {
      const s = await unwrap(api.POST('/api/workouts/sets', {
        body: { exercise_id: ex.exercise_id, set_number: doneToday.length + 1, reps, weight_kg: displayToKg(weight, units), plan_id: planId },
      }))
      onLogged(s)
    } catch (e) {
      toast(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const img = ex.exercise?.images?.[0]
  const complete = doneToday.length >= ex.sets
  return (
    <section className="card ex-card">
      <div className="ex">
        {img ? <img className="ex-img" src={img} alt="" loading="lazy" /> : <div className="ex-img" />}
        <div className="stack" style={{ gap: 4 }}>
          <div className="row between">
            <h3>{ex.name}</h3>
            {complete && <span className="done-mark small">Done</span>}
          </div>
          <p className="small"><strong className="num">{ex.sets} × {ex.reps}</strong> <span className="muted">rest {ex.rest_sec} s, {ex.exercise?.equipment}</span></p>
          {ex.note && <p className="small muted">{ex.note}</p>}
          <button className="btn btn-quiet btn-sm" style={{ justifySelf: 'start' }} onClick={() => setOpen((o) => !o)}>
            {open ? 'Hide' : doneToday.length ? `Log sets (${doneToday.length}/${ex.sets})` : 'Start'}
          </button>
        </div>
      </div>
      {open && (
        <div className="stack">
          {last.length > 0 && (
            <p className="small muted">Last time: {last.map((s) => `${s.reps} × ${kgToDisplay(s.weight_kg, units).toFixed(1)}`).join(', ')} {weightUnit(units)} — try to beat it.</p>
          )}
          {doneToday.map((s) => (
            <div key={s.id} className="set-row small">
              <span className="done-mark">{s.set_number}</span>
              <span>{s.reps} reps</span>
              <span>{kgToDisplay(s.weight_kg, units).toFixed(1)} {weightUnit(units)}</span>
              <span className="done-mark" aria-label="Logged">✓</span>
            </div>
          ))}
          <div className="set-row">
            <span className="muted small">{doneToday.length + 1}</span>
            <input className="input" type="number" inputMode="numeric" value={reps} onChange={(e) => setReps(Number(e.target.value))} aria-label="Reps" />
            <input className="input" type="number" inputMode="decimal" step="0.5" value={weight} onChange={(e) => setWeight(Number(e.target.value))} aria-label={`Weight in ${weightUnit(units)}`} />
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={logSet} aria-label="Log set">✓</button>
          </div>
          <p className="small muted">Reps · weight ({weightUnit(units)}). Logging a set starts the rest timer.</p>
          {ex.exercise?.instructions?.length ? (
            <details>
              <summary className="small" style={{ cursor: 'pointer', fontWeight: 600 }}>How to do it</summary>
              <ol className="small muted" style={{ paddingLeft: 18 }}>{ex.exercise.instructions.map((s, i) => <li key={i}>{s}</li>)}</ol>
            </details>
          ) : null}
        </div>
      )}
    </section>
  )
}
