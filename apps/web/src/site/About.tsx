import { Link } from 'react-router-dom'

export function About() {
  return (
    <div className="page-wrap">
      <section className="section split" style={{ borderTop: 0 }}>
        <h1 className="display" style={{ fontSize: 'clamp(40px, 6vw, 72px)' }}>Why we built BetterU</h1>
        <div className="stack" style={{ gap: 20, fontSize: 18, lineHeight: 1.7, maxWidth: '36em' }}>
          <p>
            Students, athletes and busy people often struggle to eat in a way that matches their goals. Advice online is
            overwhelming and inconsistent, and much of it isn't based on evidence. People end up following trends and
            influencer opinions, and professional guidance is expensive or out of reach.
          </p>
          <p>
            BetterU starts from trusted data instead. Food numbers come from USDA FoodData Central. Guidance comes from
            MedlinePlus, the World Health Organization and Health Canada. Your targets come from a published equation,
            with safety limits built in.
          </p>
          <p>
            On top of that sits Alden, a coach that looks things up before it answers, shows its sources, and only logs
            food when you say so.
          </p>
        </div>
      </section>

      <section className="section split">
        <h2 style={{ fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 850 }}>What you can do with it</h2>
        <div className="feature-list">
          <div><strong>Eat to a target</strong><p>Daily calories and macros set for your body and goal, with the working shown.</p></div>
          <div><strong>Track quickly</strong><p>Search, scan or tell Alden what you ate. Recent foods are one tap away.</p></div>
          <div><strong>Ask with confidence</strong><p>Answers cite the food database or health source they came from.</p></div>
          <div><strong>Train with a plan</strong><p>Workouts built around your goal, schedule and equipment.</p></div>
          <div><strong>See real progress</strong><p>A weight trend that ignores day-to-day noise, and maintenance calories learned from your data.</p></div>
        </div>
      </section>

      <section className="section">
        <div className="cta-band">
          <h2 style={{ fontSize: 'clamp(28px, 4vw, 44px)', fontWeight: 850 }}>Try it on your own numbers.</h2>
          <Link className="btn btn-primary" to="/app">Open BetterU</Link>
        </div>
      </section>
    </div>
  )
}
