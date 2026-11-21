import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errorMessage, unwrap, type ProfileInput, type Targets } from '../api/client'
import { useAuth } from '../auth'
import { Brand } from '../components/Logo'
import { Warnings } from '../components/Nutrition'
import { DEFAULT_PROFILE, ProfileForm, type Section } from '../components/ProfileForm'
import { round } from '../units'

const STEPS: Section[][] = [['name', 'goal'], ['body'], ['activity'], ['food'], ['training', 'notes']]

export function Onboarding() {
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [profile, setProfile] = useState<ProfileInput>(DEFAULT_PROFILE)
  const [targets, setTargets] = useState<Targets | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const last = step === STEPS.length

  // Show live targets once the body + activity steps are done.
  useEffect(() => {
    if (step < 3) return
    const t = window.setTimeout(() => {
      unwrap(api.POST('/api/profile/preview-targets', { body: profile }))
        .then((t) => { setTargets(t); setError(null) })
        .catch((e) => { setTargets(null); setError(errorMessage(e)) })
    }, 200)
    return () => window.clearTimeout(t)
  }, [profile, step])

  async function finish() {
    setSaving(true)
    setError(null)
    try {
      await unwrap(api.PUT('/api/profile', { body: profile }))
      await refresh()
      navigate('/', { replace: true })
    } catch (e) {
      setError(errorMessage(e))
      setSaving(false)
    }
  }

  return (
    <div className="center-page">
      <div className="onboard">
        <div className="row between">
          <Brand to="/" />
          <span className="small muted num">Step {Math.min(step + 1, STEPS.length + 1)} of {STEPS.length + 1}</span>
        </div>
        <div className="progress-rule" aria-label={`Step ${Math.min(step + 1, STEPS.length + 1)} of ${STEPS.length + 1}`}>
          {[...STEPS, []].map((_, i) => <span key={i} className={i <= step ? 'on' : ''} />)}
        </div>

        {!last ? (
          <ProfileForm value={profile} onChange={setProfile} sections={STEPS[step]} />
        ) : (
          <div className="stack">
            <h2>Your daily targets</h2>
            {targets ? (
              <>
                <div className="row between wrap panel">
                  <div className="stat"><strong>{round(targets.recommended_calories)}</strong><span>kcal / day</span></div>
                  <div className="stat"><strong>{round(targets.macros.protein_g)} g</strong><span>protein</span></div>
                  <div className="stat"><strong>{round(targets.macros.carbs_g)} g</strong><span>carbs</span></div>
                  <div className="stat"><strong>{round(targets.macros.fat_g)} g</strong><span>fat</span></div>
                </div>
                <Warnings warnings={targets.warnings} />
                <details>
                  <summary className="small" style={{ cursor: 'pointer', fontWeight: 600 }}>How we worked this out</summary>
                  <div className="small muted stack" style={{ marginTop: 8, gap: 4 }}>
                    <p>Resting burn (BMR, Mifflin–St Jeor): <b>{round(targets.bmr)} kcal</b></p>
                    <p>× activity factor = maintenance (TDEE): <b>{round(targets.tdee)} kcal</b></p>
                    <p>Adjusted for your goal ({targets.goal_applied}) = <b>{round(targets.recommended_calories)} kcal</b></p>
                    <p>Protein is set per kg of body weight; fat is 30% of calories; carbs fill the rest.</p>
                    <p>After two weeks of logging, BetterU estimates your real maintenance from your weight trend.</p>
                  </div>
                </details>
              </>
            ) : (
              <div className="skeleton" style={{ height: 90 }} />
            )}
            <p className="small muted">BetterU gives general guidance, not medical advice. Talk to a doctor before big changes, especially with a health condition.</p>
          </div>
        )}

        {error && <div className="alert alert-error" role="alert">{error}</div>}
        <div className="row between">
          <button className="btn btn-quiet" disabled={step === 0} onClick={() => setStep((s) => s - 1)}>Back</button>
          {last ? (
            <button className="btn btn-primary" disabled={saving || !targets} onClick={finish}>{saving ? 'Saving…' : 'Start using BetterU'}</button>
          ) : (
            <button className="btn btn-primary" onClick={() => setStep((s) => s + 1)}>Continue</button>
          )}
        </div>
      </div>
    </div>
  )
}
