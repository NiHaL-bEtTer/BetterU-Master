import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, errorMessage, todayISO, unwrap, type ChatAction, type DaySummary, type Source } from '../api/client'
import { streamChat } from '../api/chatStream'
import { IconCopy, IconDown, IconSend, IconStop, IconTrash, IconUp } from '../components/icons'
import { Card } from '../components/Dash'
import { Markdown } from '../components/Markdown'
import CallChip from '../components/rb/CallChip/CallChip'
import { useToast } from '../components/Toast'

interface Msg {
  key: string
  id?: number
  role: 'user' | 'assistant'
  content: string
  sources: Source[]
  actions: ChatAction[]
  videoId?: string | null
  rating?: number | null
  status?: string
  error?: string
  done?: boolean
}

const SUGGESTIONS = [
  'How much protein is in 200 g of chicken breast?',
  'I had 2 eggs and a slice of toast for breakfast',
  'What are good sources of iron for a vegetarian?',
  'How do I make overnight oats?',
]

export function Alden() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [loaded, setLoaded] = useState(false)
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [params, setParams] = useSearchParams()
  const abortRef = useRef<AbortController | null>(null)
  const logRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const navigate = useNavigate()
  const toast = useToast()

  const [day, setDay] = useState<DaySummary | null>(null)
  const loadDay = () => { unwrap(api.GET('/api/log/{day}', { params: { path: { day: todayISO() } } })).then(setDay).catch(() => {}) }
  useEffect(loadDay, [])

  useEffect(() => {
    unwrap(api.GET('/api/chat/messages', { params: { query: { limit: 50 } } }))
      .then((rows) => setMessages(rows.map((m) => ({
        key: `m${m.id}`, id: m.id, role: m.role, content: m.content, sources: m.sources,
        actions: m.actions, videoId: m.video_id, rating: m.rating, done: true,
      }))))
      .finally(() => setLoaded(true))
  }, [])

  // Prefill from links like /alden?q=... (from the Today page).
  useEffect(() => {
    const q = params.get('q')
    if (q) {
      setInput(q)
      setParams({}, { replace: true })
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [params, setParams])

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const patchLast = (fn: (m: Msg) => Msg) =>
    setMessages((ms) => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)))

  async function send(text: string) {
    const message = text.trim()
    if (!message || streaming) return
    setInput('')
    setStreaming(true)
    const controller = new AbortController()
    abortRef.current = controller
    setMessages((ms) => [
      ...ms,
      { key: `u${Date.now()}`, role: 'user', content: message, sources: [], actions: [], done: true },
      { key: `a${Date.now()}`, role: 'assistant', content: '', sources: [], actions: [], status: 'Thinking' },
    ])
    try {
      for await (const ev of streamChat(message, controller.signal)) {
        switch (ev.event) {
          case 'token': patchLast((m) => ({ ...m, content: m.content + ev.data.text, status: undefined })); break
          case 'status': patchLast((m) => ({ ...m, status: ev.data.text })); break
          case 'sources': patchLast((m) => ({ ...m, sources: ev.data.sources })); break
          case 'actions': patchLast((m) => ({ ...m, actions: ev.data.actions })); break
          case 'video': patchLast((m) => ({ ...m, videoId: ev.data.video_id })); break
          case 'done': patchLast((m) => ({ ...m, id: ev.data.message_id, done: true, status: undefined })); break
          case 'error': patchLast((m) => ({ ...m, error: ev.data.message, status: undefined, done: true })); break
        }
      }
    } catch (e) {
      if ((e as Error).name !== 'AbortError') patchLast((m) => ({ ...m, error: errorMessage(e, 'Connection lost.'), status: undefined }))
    } finally {
      patchLast((m) => ({ ...m, status: undefined, done: true }))
      setStreaming(false)
      abortRef.current = null
    }
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  async function runAction(msg: Msg, action: ChatAction) {
    if (action.type === 'build_workout') {
      navigate(`/app/train?request=${encodeURIComponent(String(action.payload.request ?? ''))}`)
      return
    }
    const payload = action.payload as { meal: 'breakfast' | 'lunch' | 'dinner' | 'snack'; items: { food_id: number; grams: number }[] }
    try {
      await unwrap(api.POST('/api/log/batch', { body: { meal: payload.meal, items: payload.items.map(({ food_id, grams }) => ({ food_id, grams })) } }))
      toast('Logged', `Added to ${payload.meal}`)
      loadDay()
      if (msg.id) {
        const index = msg.actions.indexOf(action)
        await api.DELETE('/api/chat/messages/{message_id}/actions/{index}', { params: { path: { message_id: msg.id, index } } })
      }
      setMessages((ms) => ms.map((m) => (m.key === msg.key ? { ...m, actions: m.actions.filter((a) => a !== action) } : m)))
    } catch (e) {
      toast(errorMessage(e))
    }
  }

  async function rate(msg: Msg, value: 1 | -1) {
    if (!msg.id) return
    const next = msg.rating === value ? 0 : value
    setMessages((ms) => ms.map((m) => (m.key === msg.key ? { ...m, rating: next || null } : m)))
    await api.POST('/api/chat/messages/{message_id}/rating', { params: { path: { message_id: msg.id } }, body: { rating: next as 0 | 1 | -1 } })
    if (next === -1) toast('Thanks for the feedback', 'It helps improve Alden.')
  }

  async function clearChat() {
    if (!confirm('Clear your whole conversation with Alden? This cannot be undone.')) return
    await api.DELETE('/api/chat/messages')
    setMessages([])
  }

  const t = day?.targets
  return (
    <div className="chat-shell">
    <div className="chat">
      <div className="row between" style={{ paddingBottom: 8 }}>
        <div><h1>Alden</h1><p className="muted small">Answers come from USDA data and trusted health sources, with links.</p></div>
        {messages.length > 0 && <button className="icon-btn" onClick={clearChat} aria-label="Clear conversation"><IconTrash /></button>}
      </div>

      <div className="chat-log" ref={logRef} aria-live="polite">
        {loaded && messages.length === 0 && (
          <div className="stack" style={{ margin: 'auto 0', gap: 16 }}>
            <div className="empty"><strong>Ask about food or training</strong>Alden looks up exact nutrition, prepares meal logs for you to confirm, and builds workout plans.</div>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => <button key={s} className="suggestion" onClick={() => send(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.key} className={`msg ${m.role}`}>
            {(m.content || m.role === 'user') && (
              <div className="bubble">{m.role === 'user' ? m.content : <Markdown text={m.content} sources={m.sources} />}</div>
            )}
            {m.status && (
              <CallChip
                key={m.status}
                icon="search"
                name={m.status.replace(/…$/, '')}
                argument=""
                showTimer={false}
                status="running"
                expectedMs={2500}
                color="var(--ink)"
                surfaceColor="var(--wash)"
                progressColor="var(--avocado)"
              />
            )}
            {m.error && <div className="alert alert-error small">{m.error}</div>}
            {m.videoId && /^[A-Za-z0-9_-]{11}$/.test(m.videoId) && (
              <iframe className="video" src={`https://www.youtube-nocookie.com/embed/${m.videoId}?rel=0`} title="Recipe video"
                allow="accelerometer; encrypted-media; picture-in-picture" allowFullScreen loading="lazy" />
            )}
            {m.actions.length > 0 && (
              <div className="row wrap">
                {m.actions.map((a, i) => (
                  <button key={i} className="btn btn-accent btn-sm" onClick={() => runAction(m, a)}>{a.label.replace(' · ', ', ')}</button>
                ))}
              </div>
            )}
            {m.sources.length > 0 && (
              <div className="sources">
                {m.sources.map((s) => (
                  <a key={s.id} className="source" href={s.url || undefined} target="_blank" rel="noopener noreferrer" title={s.title}>
                    <b>{s.id}</b>{s.title}
                  </a>
                ))}
              </div>
            )}
            {m.role === 'assistant' && m.done && m.content && (
              <div className="msg-tools">
                <button className="icon-btn" aria-label="Copy answer" onClick={() => { navigator.clipboard.writeText(m.content); toast('Copied') }}><IconCopy /></button>
                <button className="icon-btn" aria-label="Good answer" aria-pressed={m.rating === 1} onClick={() => rate(m, 1)} style={{ color: m.rating === 1 ? 'var(--avocado)' : undefined }}><IconUp /></button>
                <button className="icon-btn" aria-label="Bad answer" aria-pressed={m.rating === -1} onClick={() => rate(m, -1)} style={{ color: m.rating === -1 ? 'var(--danger)' : undefined }}><IconDown /></button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="composer">
        <textarea
          ref={inputRef} rows={1} placeholder="Ask Alden, or tell it what you ate…" value={input} maxLength={4000}
          onChange={(e) => { setInput(e.target.value); e.target.style.height = 'auto'; e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px` }}
          onKeyDown={onKey} aria-label="Message Alden"
        />
        {streaming ? (
          <button className="btn btn-quiet" onClick={() => abortRef.current?.abort()} aria-label="Stop"><IconStop width={18} height={18} /></button>
        ) : (
          <button className="btn btn-primary" disabled={!input.trim()} onClick={() => send(input)} aria-label="Send"><IconSend width={18} height={18} /></button>
        )}
      </div>
      <p className="tiny muted" style={{ textAlign: 'center', marginTop: 8 }}>Alden can make mistakes and isn't a doctor.</p>
    </div>

    <aside className="chat-rail" aria-label="Context">
      <Card title="Today so far">
        {day && t ? (
          <div className="stack" style={{ gap: 12 }}>
            <div className="row between"><span className="muted small">Calories</span><b className="num">{Math.round(day.totals.kcal)} / {Math.round(t.recommended_calories)}</b></div>
            <div className="row between"><span className="muted small">Protein</span><b className="num">{Math.round(day.totals.protein_g)} / {Math.round(t.macros.protein_g)} g</b></div>
            <div className="row between"><span className="muted small">Carbohydrate</span><b className="num">{Math.round(day.totals.carbs_g)} / {Math.round(t.macros.carbs_g)} g</b></div>
            <div className="row between"><span className="muted small">Fat</span><b className="num">{Math.round(day.totals.fat_g)} / {Math.round(t.macros.fat_g)} g</b></div>
            <p className="tiny muted">Alden sees these numbers and your profile, so answers fit your day.</p>
          </div>
        ) : <div className="skeleton" style={{ height: 120 }} />}
      </Card>
      <Card title="Try asking">
        <div className="stack" style={{ gap: 8 }}>
          {SUGGESTIONS.map((q) => <button key={q} className="suggestion small" disabled={streaming} onClick={() => send(q)}>{q}</button>)}
        </div>
      </Card>
      <Card title="How Alden answers">
        <ol className="small muted" style={{ paddingLeft: 18, margin: 0, display: 'grid', gap: 6 }}>
          <li>Looks foods up in USDA data</li>
          <li>Adds them up in code, not guesswork</li>
          <li>Links every number to its source</li>
          <li>Logs only when you tap</li>
        </ol>
      </Card>
    </aside>
    </div>
  )
}
