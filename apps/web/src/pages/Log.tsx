import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, errorMessage, todayISO, unwrap, type DaySummary, type Meal, type MealEntry } from '../api/client'
import { useWide } from '../components/Dash'
import { Facts } from '../components/Facts'
import { FoodPicker } from '../components/FoodPicker'
import { IconTrash } from '../components/icons'
import SwipeRow from '../components/rb/SwipeRow/SwipeRow'
import { useToast } from '../components/Toast'
import { round } from '../units'

const MEALS: Meal[] = ['breakfast', 'lunch', 'dinner', 'snack']

function shift(iso: string, days: number) {
  const d = new Date(`${iso}T12:00:00`)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

const isTouch = typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches

export function Log() {
  const [params, setParams] = useSearchParams()
  const [date, setDate] = useState(todayISO())
  const [day, setDay] = useState<DaySummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const q = params.get('q') ?? ''
  const hour = new Date().getHours()
  const adding = (params.get('meal') as Meal | null) ?? (q ? (hour < 11 ? 'breakfast' : hour < 15 ? 'lunch' : hour < 21 ? 'dinner' : 'snack') : null)
  const toast = useToast()
  const wide = useWide()

  const load = useCallback(() => {
    unwrap(api.GET('/api/log/{day}', { params: { path: { day: date } } })).then(setDay).catch((e) => setError(errorMessage(e)))
  }, [date])
  useEffect(load, [load])

  useEffect(() => {
    if (!adding) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setParams({})
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [adding, setParams])

  async function remove(entry: MealEntry) {
    setDay((d) => d && { ...d, entries: d.entries.filter((e) => e.id !== entry.id) })
    await api.DELETE('/api/log/{entry_id}', { params: { path: { entry_id: entry.id } } })
    toast('Removed', entry.name)
    load()
  }

  const isToday = date === todayISO()
  const label = isToday ? 'Today' : new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
  const t = day?.targets

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Food log</h1>
          {day && t && (
            <p className="num">{round(day.totals.kcal)} of {round(t.recommended_calories)} kcal, {round(day.totals.protein_g)} g protein</p>
          )}
        </div>
        <div className="day-switch">
          <button className="icon-btn" onClick={() => setDate((d) => shift(d, -1))} aria-label="Previous day">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M15 6l-6 6 6 6" /></svg>
          </button>
          <strong>{label}</strong>
          <button className="icon-btn" disabled={isToday} onClick={() => setDate((d) => shift(d, 1))} aria-label="Next day">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 6l6 6-6 6" /></svg>
          </button>
        </div>
      </header>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="split-rail">
      <div className="stack" style={{ gap: 18 }}>
      {MEALS.map((m) => {
        const items = day?.entries.filter((e) => e.meal === m) ?? []
        const kcal = items.reduce((s, e) => s + e.kcal, 0)
        return (
          <section className="card" key={m}>
            <div className="card-head">
              <h2 style={{ textTransform: 'capitalize' }}>{m}</h2>
              <div className="row">
                {items.length > 0 && <span className="small muted num">{round(kcal)} kcal</span>}
                <button className="btn btn-line btn-sm" onClick={() => setParams({ meal: m })}>Add food</button>
              </div>
            </div>
            {!day ? <div className="skeleton" style={{ height: 40 }} />
              : items.length === 0 ? <p className="small muted">Nothing logged.</p>
              : (
                <div className="stack" style={{ gap: 4 }}>
                  {items.map((e) => {
                    const body = (
                      <div className="entry-row">
                        <div style={{ minWidth: 0 }}>
                          <div className="list-title truncate">{e.name}</div>
                          <div className="small muted num truncate">{round(e.grams)} g, {round(e.protein_g)} g protein, {round(e.carbs_g)} g carbs, {round(e.fat_g)} g fat</div>
                        </div>
                        <div className="row" style={{ gap: 2 }}>
                          <strong className="num small" style={{ whiteSpace: 'nowrap' }}>{round(e.kcal)} kcal</strong>
                          {!isTouch && <button className="icon-btn" onClick={() => remove(e)} aria-label={`Remove ${e.name}`}><IconTrash /></button>}
                        </div>
                      </div>
                    )
                    return isTouch ? (
                      <SwipeRow
                        key={e.id}
                        label={e.name}
                        height={64}
                        radius={10}
                        rowColor="var(--paper)"
                        textColor="var(--ink)"
                        drawerColor="var(--danger)"
                        actions={[{ id: 'delete', label: 'Remove', color: 'var(--danger)', dismiss: true }]}
                        onCommit={() => remove(e)}
                        onAction={() => remove(e)}
                      >
                        {body}
                      </SwipeRow>
                    ) : <div key={e.id} className="list-row" style={{ padding: '10px 0' }}>{body}</div>
                  })}
                  {isTouch && <p className="tiny muted">Swipe left on a food to remove it.</p>}
                </div>
              )}
          </section>
        )
      })}

      </div>

      <aside className="rail">
        {adding && wide && (
          <section className="card">
            <div className="card-head">
              <h2>Add to {adding}</h2>
              <button className="btn btn-quiet btn-sm" onClick={() => setParams({})}>Done</button>
            </div>
            <FoodPicker key={`${adding}-${q}`} meal={adding} date={date} initialQuery={q} onAdded={() => { toast(`Added to ${adding}`); setParams({}); load() }} />
          </section>
        )}
        {day && t ? (
          <Facts
            title={isToday ? 'Today' : label}
            subtitle={`${day.entries.length} ${day.entries.length === 1 ? 'food' : 'foods'} logged, target ${round(t.recommended_calories)} kcal`}
            heroLabel="Calories"
            heroValue={round(day.totals.kcal)}
            rows={[
              { label: 'Protein', amount: `${round(day.totals.protein_g)} g`, share: day.totals.protein_g / t.macros.protein_g },
              { label: 'Carbohydrate', amount: `${round(day.totals.carbs_g)} g`, share: day.totals.carbs_g / t.macros.carbs_g },
              { label: 'Fat', amount: `${round(day.totals.fat_g)} g`, share: day.totals.fat_g / t.macros.fat_g },
            ]}
            foot={`${round(Math.max(t.recommended_calories - day.totals.kcal, 0))} kcal left for the day.`}
          />
        ) : <div className="skeleton" style={{ height: 300 }} />}
      </aside>
      </div>

      {adding && !wide && (
        <div className="sheet-backdrop" onClick={(e) => e.target === e.currentTarget && setParams({})}>
          <div className="sheet stack" role="dialog" aria-modal="true" aria-label={`Add food to ${adding}`}>
            <div className="panel-head" style={{ marginBottom: 4 }}>
              <h2>Add to {adding}</h2>
              <button className="btn btn-quiet btn-sm" onClick={() => setParams({})}>Close</button>
            </div>
            <FoodPicker meal={adding} date={date} initialQuery={q} onAdded={() => { toast(`Added to ${adding}`); setParams({}); load() }} />
          </div>
        </div>
      )}
    </div>
  )
}
