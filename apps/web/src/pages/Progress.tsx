import { useEffect, useState, type FormEvent } from 'react'
import { api, errorMessage, unwrap, type Progress as ProgressData } from '../api/client'
import { useToast } from '../components/Toast'
import { HeroCard } from '../components/Dash'
import { TrendChart } from '../components/TrendChart'
import { displayToKg, formatWeight, round, weightUnit, type Units } from '../units'

export function Progress() {
  const [data, setData] = useState<ProgressData | null>(null)
  const [units, setUnits] = useState<Units>('metric')
  const [weight, setWeight] = useState('')
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    unwrap(api.GET('/api/progress')).then(setData).catch((e) => setError(errorMessage(e)))
    api.GET('/api/profile').then(({ data }) => data && setUnits(data.profile.units as Units))
  }, [])

  async function save(e: FormEvent) {
    e.preventDefault()
    const v = Number(weight)
    if (!v) return
    try {
      setData(await unwrap(api.POST('/api/progress/weight', { body: { weight_kg: displayToKg(v, units) } })))
      setWeight('')
      toast('Weight saved')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const pts = data?.weights ?? []
  const latest = pts.at(-1)
  const weekAgo = pts.filter((p) => latest && (new Date(latest.date).getTime() - new Date(p.date).getTime()) / 86400000 >= 7).at(-1)
  const change = latest && weekAgo ? latest.trend_kg - weekAgo.trend_kg : null

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Progress</h1><p>Your weight trend and what your logs say about your real maintenance calories.</p></div>
      </div>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="split-rail">
        <section className="card">
          <div className="card-head">
            <h2>Weight trend</h2>
            {latest && <span className="small muted num">{formatWeight(latest.trend_kg, units)}{change !== null && `, ${change >= 0 ? '+' : ''}${formatWeight(change, units)} this week`}</span>}
          </div>
          {data ? <TrendChart points={pts} units={units} /> : <div className="skeleton" style={{ height: 260 }} />}
          <p className="small muted" style={{ marginTop: 12 }}>Dots are daily weigh-ins. The line is a 7-day average, which ignores water and food swings.</p>
        </section>

        <aside className="rail">
          <section className="card">
            <div className="card-head"><h2>Weigh in</h2></div>
            <form className="row" onSubmit={save}>
              <div className="input-unit" style={{ flex: 1 }}>
                <input className="input" type="number" inputMode="decimal" step="0.1" placeholder="Today's weight"
                  value={weight} onChange={(e) => setWeight(e.target.value)} aria-label={`Today's weight in ${weightUnit(units)}`} />
                <span>{weightUnit(units)}</span>
              </div>
              <button className="btn btn-primary" disabled={!weight}>Save</button>
            </form>
            <p className="small muted" style={{ marginTop: 10 }}>Same time each morning gives the cleanest trend.</p>
          </section>

          <HeroCard>
            <div className="stack" style={{ gap: 14 }}>
              <p className="muted small">Maintenance calories</p>
              <div className="row" style={{ gap: 28, alignItems: 'flex-end' }}>
                <div className="stat"><strong style={{ color: 'var(--leaf)', fontSize: 34 }}>{data?.estimated_tdee ? round(data.estimated_tdee) : '—'}</strong><span style={{ color: 'var(--on-forest-muted)' }}>from your data</span></div>
                <div className="stat"><strong style={{ color: 'var(--on-forest)' }}>{round(data?.formula_tdee)}</strong><span style={{ color: 'var(--on-forest-muted)' }}>formula estimate</span></div>
              </div>
              <p className="small" style={{ color: 'var(--on-forest-muted)' }}>{data?.message}</p>
              <p className="tiny" style={{ color: 'var(--on-forest-muted)' }}>{data?.logged_days_last_14 ?? 0} fully logged days in the last two weeks.</p>
            </div>
          </HeroCard>
        </aside>
      </div>
    </div>
  )
}
