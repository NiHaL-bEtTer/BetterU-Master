import { useEffect, useRef, useState } from 'react'
import { api, errorMessage, unwrap, type Food, type Meal } from '../api/client'
import { round } from '../units'
import { Facts } from './Facts'
import { IconBarcode, IconStar } from './icons'
import RubberSegment from './rb/RubberSegment/RubberSegment'

type Tab = 'search' | 'recent' | 'favorites'

interface Props {
  meal: Meal
  date: string
  onAdded: () => void
  initialQuery?: string
}

/** Find a food (search, recent, favourites or barcode), pick a portion, and log it. */
export function FoodPicker({ meal, date, onAdded, initialQuery = '' }: Props) {
  const [tab, setTab] = useState<Tab>('search')
  const [query, setQuery] = useState(initialQuery)
  const [results, setResults] = useState<Food[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Food | null>(null)
  const [favorites, setFavorites] = useState<Set<number>>(new Set())
  const [barcodeOpen, setBarcodeOpen] = useState(false)

  // Favourites are needed on every tab to draw the star state.
  useEffect(() => {
    unwrap(api.GET('/api/foods/favorites')).then((f) => setFavorites(new Set(f.map((x) => x.id)))).catch(() => {})
  }, [])

  useEffect(() => {
    setError(null)
    if (tab !== 'search') {
      setLoading(true)
      const req = tab === 'recent' ? api.GET('/api/foods/recent') : api.GET('/api/foods/favorites')
      unwrap(req).then(setResults).catch((e) => setError(errorMessage(e))).finally(() => setLoading(false))
      return
    }
    const q = query.trim()
    if (q.length < 2) {
      setResults([])
      return
    }
    setLoading(true)
    const t = window.setTimeout(() => {
      unwrap(api.GET('/api/foods/search', { params: { query: { q } } }))
        .then(setResults)
        .catch((e) => setError(errorMessage(e)))
        .finally(() => setLoading(false))
    }, 250)
    return () => window.clearTimeout(t)
  }, [query, tab])

  async function toggleFavorite(food: Food) {
    const on = favorites.has(food.id)
    const next = new Set(favorites)
    if (on) next.delete(food.id)
    else next.add(food.id)
    setFavorites(next)
    const params = { params: { path: { food_id: food.id } } }
    await (on ? api.DELETE('/api/foods/{food_id}/favorite', params) : api.PUT('/api/foods/{food_id}/favorite', params))
  }

  if (selected) {
    return <PortionForm food={selected} meal={meal} date={date} onBack={() => setSelected(null)} onAdded={onAdded} />
  }

  return (
    <div className="stack">
      <RubberSegment
        aria-label="Find food"
        items={[{ value: 'search', label: 'Search' }, { value: 'recent', label: 'Recent' }, { value: 'favorites', label: 'Favourites' }]}
        value={tab}
        onChange={(v) => setTab(v as Tab)}
        trackColor="var(--wash)"
        thumbColor="var(--paper)"
        textColor="var(--stone)"
        activeTextColor="var(--ink)"
        size="sm"
      />
      {tab === 'search' && (
        <div className="row">
          <input
            className="input" autoFocus placeholder="Search foods, e.g. greek yogurt" value={query}
            onChange={(e) => setQuery(e.target.value)} aria-label="Search foods"
          />
          <button className="btn btn-quiet" onClick={() => setBarcodeOpen((v) => !v)} aria-label="Look up a barcode" aria-pressed={barcodeOpen}>
            <IconBarcode width={18} height={18} />
          </button>
        </div>
      )}
      {barcodeOpen && tab === 'search' && <BarcodeLookup onFound={setSelected} />}
      {error && <div className="alert alert-error">{error}</div>}
      <div className="stack" style={{ gap: 2, maxHeight: 420, overflowY: 'auto' }}>
        {loading && [0, 1, 2].map((i) => <div key={i} className="skeleton" style={{ height: 44 }} />)}
        {!loading && results.map((f) => (
          <div key={f.id} className="row" style={{ gap: 4 }}>
            <button className="food-hit" onClick={() => setSelected(f)}>
              <span style={{ minWidth: 0 }}>
                <span className="list-title" style={{ display: 'block' }}>{f.name}</span>
                <span className="muted small num" style={{ display: 'block' }}>{round(f.kcal)} kcal per 100 g{f.category ? `, ${f.category}` : ''}</span>
              </span>
            </button>
            <button className="icon-btn" onClick={() => toggleFavorite(f)} aria-label={favorites.has(f.id) ? 'Remove favourite' : 'Add favourite'}>
              <IconStar filled={favorites.has(f.id)} style={{ color: favorites.has(f.id) ? 'var(--avocado)' : undefined }} />
            </button>
          </div>
        ))}
        {!loading && !results.length && (tab !== 'search' || query.trim().length >= 2) && (
          <div className="empty">
            <strong>{tab === 'search' ? 'No matches' : tab === 'recent' ? 'Nothing logged yet' : 'No favourites yet'}</strong>
            {tab === 'search' ? 'Try a simpler name, like "rice" or "chicken".' : tab === 'favorites' ? 'Tap the star on any food to save it here.' : 'Foods you log show up here for quick re-adding.'}
          </div>
        )}
      </div>
    </div>
  )
}

function PortionForm({ food, meal, date, onBack, onAdded }: { food: Food; meal: Meal; date: string; onBack: () => void; onAdded: () => void }) {
  const options = [...(food.portions ?? []).map((p) => ({ label: `${p.description} (${round(p.grams)} g)`, grams: p.grams })), { label: 'grams', grams: 1 }]
  const [choice, setChoice] = useState(0)
  const [amount, setAmount] = useState(options.length > 1 ? 1 : 100)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const grams = options[choice].grams * (Number(amount) || 0)
  const f = grams / 100
  const macro = (v?: number | null) => (v ?? 0) * f

  async function add() {
    setSaving(true)
    setError(null)
    try {
      await unwrap(api.POST('/api/log', { body: { food_id: food.id, grams: Math.round(grams * 10) / 10, meal, eaten_on: date } }))
      onAdded()
    } catch (e) {
      setError(errorMessage(e))
      setSaving(false)
    }
  }

  return (
    <div className="stack">
      <button className="btn btn-quiet btn-sm" style={{ justifySelf: 'start' }} onClick={onBack}>Back to results</button>
      <div>
        <h3>{food.name}</h3>
        <p className="muted small">{food.category}</p>
      </div>
      <div className="grid-2">
        <label className="field">Amount
          <input className="input" type="number" inputMode="decimal" min={0} step="any" value={amount}
            onChange={(e) => setAmount(Number(e.target.value))} />
        </label>
        <label className="field">Unit
          <select className="input" value={choice} onChange={(e) => { const i = Number(e.target.value); setChoice(i); setAmount(options[i].grams === 1 ? 100 : 1) }}>
            {options.map((o, i) => <option key={o.label} value={i}>{o.label}</option>)}
          </select>
        </label>
      </div>
      <Facts
        title="Nutrition Facts"
        subtitle={`${round(grams)} g, from ${food.source === 'off' ? 'Open Food Facts' : 'USDA FoodData Central'}`}
        heroLabel="Calories"
        heroValue={round(macro(food.kcal))}
        rows={[
          { label: 'Protein', amount: `${round(macro(food.protein_g), 1)} g` },
          { label: 'Carbohydrate', amount: `${round(macro(food.carbs_g), 1)} g` },
          ...(food.fiber_g != null ? [{ label: 'Fibre', amount: `${round(macro(food.fiber_g), 1)} g`, sub: true }] : []),
          ...(food.sugar_g != null ? [{ label: 'Sugars', amount: `${round(macro(food.sugar_g), 1)} g`, sub: true }] : []),
          { label: 'Fat', amount: `${round(macro(food.fat_g), 1)} g` },
          ...(food.sodium_mg != null ? [{ label: 'Sodium', amount: `${round(macro(food.sodium_mg))} mg` }] : []),
        ]}
      />
      {error && <div className="alert alert-error">{error}</div>}
      <button className="btn btn-primary btn-block" disabled={saving || grams <= 0} onClick={add}>
        {saving ? 'Adding…' : `Add to ${meal}`}
      </button>
    </div>
  )
}

interface DetectedBarcode { rawValue: string }
interface BarcodeDetectorLike { detect(source: CanvasImageSource): Promise<DetectedBarcode[]> }
declare global { interface Window { BarcodeDetector?: new (opts: { formats: string[] }) => BarcodeDetectorLike } }

function BarcodeLookup({ onFound }: { onFound: (f: Food) => void }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [scanning, setScanning] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canScan = typeof window !== 'undefined' && !!window.BarcodeDetector && !!navigator.mediaDevices

  async function lookup(value: string) {
    setBusy(true)
    setError(null)
    try {
      onFound(await unwrap(api.GET('/api/foods/barcode/{code}', { params: { path: { code: value.trim() } } })))
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (!scanning || !window.BarcodeDetector) return
    let stream: MediaStream | null = null
    let raf = 0
    let stopped = false
    const detector = new window.BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e'] })
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }).then((s) => {
      stream = s
      const v = videoRef.current
      if (!v) return
      v.srcObject = s
      v.play()
      const tick = async () => {
        if (stopped) return
        try {
          const found = await detector.detect(v)
          if (found[0]?.rawValue) {
            setScanning(false)
            setCode(found[0].rawValue)
            lookup(found[0].rawValue)
            return
          }
        } catch { /* frame not ready */ }
        raf = requestAnimationFrame(tick)
      }
      tick()
    }).catch(() => { setError('Camera access was blocked. Type the barcode instead.'); setScanning(false) })
    return () => { stopped = true; cancelAnimationFrame(raf); stream?.getTracks().forEach((t) => t.stop()) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanning])

  return (
    <div className="panel stack">
      <p className="small muted">Packaged food? Look it up by barcode (data from Open Food Facts).</p>
      {scanning && <video ref={videoRef} className="video" muted playsInline />}
      <div className="row">
        <input className="input" inputMode="numeric" placeholder="e.g. 737628064502" value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} aria-label="Barcode number" />
        <button className="btn btn-primary" disabled={busy || code.length < 6} onClick={() => lookup(code)}>{busy ? 'Finding' : 'Find'}</button>
      </div>
      {canScan && <button className="btn btn-line btn-sm" onClick={() => setScanning((s) => !s)}>{scanning ? 'Stop camera' : 'Scan with camera'}</button>}
      {error && <div className="alert alert-error">{error}</div>}
    </div>
  )
}
