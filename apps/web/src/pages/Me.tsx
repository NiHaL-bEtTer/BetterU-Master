import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, errorMessage, unwrap, type ProfileInput, type Targets } from '../api/client'
import { useAuth } from '../auth'
import { Facts } from '../components/Facts'
import { ProfileForm } from '../components/ProfileForm'
import HoldButton from '../components/rb/HoldButton/HoldButton'
import { useToast } from '../components/Toast'
import { round } from '../units'

export function Me() {
  const { refresh } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [profile, setProfile] = useState<ProfileInput | null>(null)
  const [targets, setTargets] = useState<Targets | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    unwrap(api.GET('/api/profile'))
      .then((d) => { setProfile(d.profile); setTargets(d.targets) })
      .catch(() => navigate('/onboarding', { replace: true }))
  }, [navigate])

  async function save() {
    if (!profile) return
    setSaving(true)
    setError(null)
    try {
      const d = await unwrap(api.PUT('/api/profile', { body: profile }))
      setProfile(d.profile)
      setTargets(d.targets)
      toast('Profile saved', 'Your targets are updated.')
      refresh()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  async function exportData() {
    const data = await unwrap(api.GET('/api/profile/export'))
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    const a = Object.assign(document.createElement('a'), { href: url, download: 'betteru-data.json' })
    a.click()
    URL.revokeObjectURL(url)
  }

  async function resetDevice() {
    await api.DELETE('/api/profile/account')
    // Reloading creates a fresh device account and opens onboarding.
    window.location.assign(`${import.meta.env.BASE_URL}onboarding`)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Profile</h1><p>Your data is saved to this browser's BetterU account.</p></div>
      </div>

      <div className="split-rail">
      <section className="card stack">
        {profile ? (
          <>
            <ProfileForm value={profile} onChange={setProfile} sections={['goal', 'body', 'activity', 'food', 'training', 'notes']} />
            {error && <div className="alert alert-error">{error}</div>}
            <button className="btn btn-primary" disabled={saving} onClick={save}>{saving ? 'Saving…' : 'Save changes'}</button>
          </>
        ) : <div className="skeleton" style={{ height: 300 }} />}
      </section>

      <aside className="rail">
        {targets && (
          <Facts
            title="Your targets"
            subtitle={`Daily, to ${targets.goal_applied === 'cut' ? 'lose fat' : targets.goal_applied === 'bulk' ? 'build muscle' : 'maintain'}`}
            heroLabel="Calories"
            heroValue={round(targets.recommended_calories)}
            rows={[
              { label: 'Protein', amount: `${round(targets.macros.protein_g)} g` },
              { label: 'Carbohydrate', amount: `${round(targets.macros.carbs_g)} g` },
              { label: 'Fat', amount: `${round(targets.macros.fat_g)} g` },
            ]}
            foot={[`Resting burn ${round(targets.bmr)} kcal, maintenance ${round(targets.tdee)} kcal, BMI ${targets.bmi}.`, ...targets.warnings].join(' ')}
          />
        )}
      <section className="card stack">
        <h2>Your data</h2>
        <p className="small muted">There's no sign-in: this browser holds a private key to your BetterU data. Clearing this site's cookies or switching browsers starts a fresh account, so download your data first if you want a copy. Chat messages and your profile are sent to the AI provider to generate Alden's answers.</p>
        <p className="small muted">Deleting removes your profile, food log, workouts and chats from BetterU. Hold the button to confirm.</p>
        <div className="row wrap">
          <button className="btn btn-line btn-sm" onClick={exportData}>Download my data</button>
          <HoldButton
            onHold={resetDevice}
            holdTime={1600}
            size="sm"
            radius={10}
            backgroundColor="var(--danger-wash)"
            textColor="var(--danger)"
            fillColor="var(--danger)"
            fillTextColor="#ffffff"
            doneLabel="Deleting"
          >
            Hold to delete my data
          </HoldButton>
        </div>
      </section>
      </aside>
      </div>
    </div>
  )
}
