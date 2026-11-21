import { useState } from 'react'
import type { ProfileInput } from '../api/client'
import RubberSegment from './rb/RubberSegment/RubberSegment'
import { cmToFtIn, displayToKg, ftInToCm, kgToDisplay, type Units } from '../units'

export const ACTIVITY = [
  { value: 'sedentary', label: 'Sedentary', hint: 'Desk job, little exercise' },
  { value: 'light', label: 'Light', hint: 'Exercise 1–3 days a week' },
  { value: 'moderate', label: 'Moderate', hint: 'Exercise 3–5 days a week' },
  { value: 'active', label: 'Active', hint: 'Hard exercise 6–7 days' },
  { value: 'very_active', label: 'Very active', hint: 'Physical job + training' },
] as const

export const GOALS = [
  { value: 'cut', label: 'Lose fat', hint: 'A gentle calorie deficit' },
  { value: 'maintain', label: 'Maintain', hint: 'Stay where you are' },
  { value: 'bulk', label: 'Build muscle', hint: 'A small calorie surplus' },
] as const

export const DIETS = ['none', 'vegetarian', 'vegan', 'pescatarian', 'halal', 'kosher'] as const
export const COMMON_ALLERGIES = ['peanut', 'tree nut', 'milk', 'egg', 'wheat', 'soy', 'fish', 'shellfish', 'sesame']
export const EQUIPMENT = [
  { value: 'dumbbell', label: 'Dumbbells' }, { value: 'barbell', label: 'Barbell' },
  { value: 'kettlebells', label: 'Kettlebells' }, { value: 'cable', label: 'Cable machine' },
  { value: 'machine', label: 'Machines' }, { value: 'bands', label: 'Resistance bands' },
  { value: 'e-z curl bar', label: 'EZ bar' }, { value: 'exercise ball', label: 'Exercise ball' },
  { value: 'medicine ball', label: 'Medicine ball' },
]

export const DEFAULT_PROFILE: ProfileInput = {
  age: 25, sex: 'female', height_cm: 168, weight_kg: 65, activity: 'moderate', goal: 'maintain',
  units: 'metric', diet: 'none', allergies: [], equipment: [], training_days: 3, notes: '',
}

export type Section = 'name' | 'goal' | 'body' | 'activity' | 'food' | 'training' | 'notes'

interface Props {
  value: ProfileInput
  onChange: (v: ProfileInput) => void
  sections: Section[]
}

export function ProfileForm({ value: v, onChange, sections }: Props) {
  const set = <K extends keyof ProfileInput>(k: K, val: ProfileInput[K]) => onChange({ ...v, [k]: val })
  const units = (v.units ?? 'metric') as Units
  const toggle = (k: 'allergies' | 'equipment', item: string) => {
    const list = v[k] ?? []
    set(k, list.includes(item) ? list.filter((x) => x !== item) : [...list, item])
  }
  const [customAllergy, setCustomAllergy] = useState('')
  const { ft, inches } = cmToFtIn(v.height_cm)

  return (
    <div className="stack" style={{ gap: 20 }}>
      {sections.includes('name') && (
        <label className="field">What should Alden call you? (optional)
          <input className="input" autoComplete="given-name" maxLength={100} value={v.name ?? ''}
            onChange={(e) => set('name', e.target.value)} placeholder="Your first name" />
        </label>
      )}

      {sections.includes('goal') && (
        <fieldset className="stack" style={{ border: 0, padding: 0, margin: 0 }}>
          <legend style={{ padding: 0 }}><h2 style={{ marginBottom: 12 }}>What's your main goal?</h2></legend>
          <div className="choices three">
            {GOALS.map((g) => (
              <button type="button" key={g.value} className="choice" onClick={() => set('goal', g.value)} aria-pressed={v.goal === g.value}>
                <strong>{g.label}</strong><span>{g.hint}</span>
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {sections.includes('body') && (
        <div className="stack">
          <div className="row between wrap">
            <h2>About you</h2>
            <RubberSegment
              aria-label="Units"
              items={[{ value: 'metric', label: 'kg, cm' }, { value: 'imperial', label: 'lb, ft' }]}
              value={units}
              onChange={(u) => set('units', u as Units)}
              trackColor="var(--wash)" thumbColor="var(--paper)" textColor="var(--stone)" activeTextColor="var(--ink)" size="sm"
            />
          </div>
          <RubberSegment
            aria-label="Sex"
            items={[{ value: 'female', label: 'Female' }, { value: 'male', label: 'Male' }]}
            value={v.sex}
            onChange={(sx) => set('sex', sx as ProfileInput['sex'])}
            trackColor="var(--wash)" thumbColor="var(--ink)" textColor="var(--stone)" activeTextColor="var(--paper)"
          />
          <p className="muted small">Used only for the metabolic-rate formula.</p>
          <div className="grid-2">
            <label className="field">Age
              <input className="input" type="number" inputMode="numeric" min={13} max={100} value={v.age} onChange={(e) => set('age', Number(e.target.value))} />
            </label>
            <label className="field">Weight
              <div className="input-unit">
                <input className="input" type="number" inputMode="decimal" step="0.1"
                  value={Number(kgToDisplay(v.weight_kg, units).toFixed(1))}
                  onChange={(e) => set('weight_kg', displayToKg(Number(e.target.value), units))} />
                <span>{units === 'imperial' ? 'lb' : 'kg'}</span>
              </div>
            </label>
          </div>
          {units === 'metric' ? (
            <label className="field">Height
              <div className="input-unit">
                <input className="input" type="number" inputMode="decimal" value={Math.round(v.height_cm)} onChange={(e) => set('height_cm', Number(e.target.value))} />
                <span>cm</span>
              </div>
            </label>
          ) : (
            <div className="grid-2">
              <label className="field">Height (ft)
                <input className="input" type="number" inputMode="numeric" value={ft} onChange={(e) => set('height_cm', ftInToCm(Number(e.target.value), inches))} />
              </label>
              <label className="field">Height (in)
                <input className="input" type="number" inputMode="numeric" value={inches} onChange={(e) => set('height_cm', ftInToCm(ft, Number(e.target.value)))} />
              </label>
            </div>
          )}
        </div>
      )}

      {sections.includes('activity') && (
        <div className="stack">
          <h2>How active are you?</h2>
          <div className="choices">
            {ACTIVITY.map((a) => (
              <button type="button" key={a.value} className="choice" onClick={() => set('activity', a.value)} aria-pressed={v.activity === a.value}>
                <strong>{a.label}</strong><span>{a.hint}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {sections.includes('food') && (
        <div className="stack">
          <h2>Food preferences</h2>
          <label className="field">Diet
            <select className="input" value={v.diet} onChange={(e) => set('diet', e.target.value as ProfileInput['diet'])}>
              {DIETS.map((d) => <option key={d} value={d}>{d === 'none' ? 'No restrictions' : d[0].toUpperCase() + d.slice(1)}</option>)}
            </select>
          </label>
          <div className="field">Allergies — Alden will never suggest these
            <div className="chips">
              {[...new Set([...COMMON_ALLERGIES, ...(v.allergies ?? [])])].map((a) => (
                <button type="button" key={a} className="chip" onClick={() => toggle('allergies', a)} aria-pressed={v.allergies?.includes(a)}>{a}</button>
              ))}
            </div>
            <form className="row" onSubmit={(e) => { e.preventDefault(); const a = customAllergy.trim().toLowerCase(); if (a) { toggle('allergies', a); setCustomAllergy('') } }}>
              <input className="input" placeholder="Add another (e.g. kiwi)" value={customAllergy} onChange={(e) => setCustomAllergy(e.target.value)} />
              <button className="btn btn-quiet" type="submit">Add</button>
            </form>
          </div>
        </div>
      )}

      {sections.includes('training') && (
        <div className="stack">
          <h2>Training</h2>
          <label className="field">Days per week: {v.training_days}
            <input type="range" min={1} max={7} value={v.training_days} onChange={(e) => set('training_days', Number(e.target.value))} />
          </label>
          <div className="field">Equipment you can use (body weight is always included)
            <div className="chips">
              {EQUIPMENT.map((e) => (
                <button type="button" key={e.value} className="chip" onClick={() => toggle('equipment', e.value)} aria-pressed={v.equipment?.includes(e.value)}>{e.label}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {sections.includes('notes') && (
        <label className="field">Anything else Alden should know? (optional)
          <textarea className="input" maxLength={4000} placeholder="e.g. I train before work, I don't like fish, recovering from a knee injury…"
            value={v.notes} onChange={(e) => set('notes', e.target.value)} />
        </label>
      )}
    </div>
  )
}
