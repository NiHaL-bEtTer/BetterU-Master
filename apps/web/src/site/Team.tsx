import { Link } from 'react-router-dom'
import { FOUNDERS } from './founders'

export function Team() {
  const team = FOUNDERS.filter((f) => !f.lead)
  const lead = FOUNDERS.find((f) => f.lead)!
  return (
    <>
      <section className="lx-section" style={{ paddingBottom: 0 }}>
        <div className="page-wrap">
          <h1 className="lx-h2" style={{ fontSize: 'clamp(48px, 8vw, 112px)' }}>A, L, D, E, N.</h1>
          <p className="lx-sub">
            BetterU's coach is named after its five founders, in this order. We're students building an evidence-based
            nutrition assistant as an ML and AI mentorship project.
          </p>
          <div className="tm-list">
            {team.map((f) => (
              <article key={f.name} className="tm-row">
                <span className="tm-glyph" aria-hidden="true">{f.name[0]}</span>
                <div><h2>{f.name}</h2><div className="tm-role">{f.role}</div></div>
                <p>{f.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="lx-section" style={{ paddingTop: 24 }}>
        <div className="page-wrap">
          <article className="tm-lead lx-dark">
            <span className="tm-lead-glyph" aria-hidden="true">N</span>
            <div className="tm-lead-copy">
              <span className="lx-lead-tag">Project lead</span>
              <h2>{lead.name}</h2>
              <div className="tm-role" style={{ color: 'var(--leaf)' }}>{lead.role}</div>
              <p>{lead.body}</p>
              <Link className="btn btn-leaf" to="/app">Try what we built</Link>
            </div>
          </article>
        </div>
      </section>
    </>
  )
}
