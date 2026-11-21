import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Facts } from '../components/Facts'
import { Reveal } from '../components/Reveal'
import ScrollReveal from '../components/rb/ScrollReveal/ScrollReveal'
import Aurora from '../components/rb/Aurora/Aurora'
import CountUp from '../components/rb/CountUp/CountUp'
import LogoLoop from '../components/rb/LogoLoop/LogoLoop'
import Silk from '../components/rb/Silk/Silk'
import SpecularButton from '../components/rb/SpecularButton/SpecularButton'
import StarBorder from '../components/rb/StarBorder/StarBorder'
import TextType from '../components/rb/TextType/TextType'
import { FOUNDERS } from './founders'

// A real answer from BetterU's food data (USDA FoodData Central), against a sample 1,650 kcal target.
const DEMO = {
  said: '2 large eggs and a slice of whole-wheat toast',
  kcal: 240,
  rows: [
    { label: 'Protein', grams: 16.9, target: 145 },
    { label: 'Carbohydrate', grams: 16.6, target: 145 },
    { label: 'Fat', grams: 11.3, target: 55 },
  ],
  target: 1650,
}

const STEPS = [
  { title: 'Looks the food up', body: 'Searches 13,600 USDA foods, plus packaged products by name or barcode, with real portion sizes.' },
  { title: 'Does the maths in code', body: 'Totals and daily targets are calculated by BetterU. The language model never guesses a number.' },
  { title: 'Shows where it came from', body: 'Each figure links back to USDA, MedlinePlus, WHO or Health Canada, so you can check it.' },
  { title: 'Waits for you', body: 'Nothing is added to your log until you tap to confirm it.' },
]

const SOURCES = [
  { name: 'USDA FoodData Central', what: 'Whole foods and common dishes, per 100 g, with real portions', count: '13,600' },
  { name: 'USDA branded foods', what: 'Packaged products, fetched the first time you search for one', count: 'On demand' },
  { name: 'MedlinePlus', what: 'Nutrition articles from the US National Library of Medicine', count: '34' },
  { name: 'World Health Organization', what: 'Fact sheets on healthy diet, sodium and physical activity', count: '6' },
  { name: 'Health Canada', what: "Canada's dietary guidelines", count: '1' },
  { name: 'free-exercise-db', what: 'Exercises with step-by-step instructions and photos', count: '876' },
]

const LOOP = ['USDA FoodData Central', 'MedlinePlus', 'World Health Organization', 'Health Canada', 'Open Food Facts', 'free-exercise-db']

const POINTS = [
  { title: 'One label for your whole day', body: 'Calories left, protein, carbs and fat against targets set for your body.' },
  { title: 'Tell Alden what you ate', body: '"Two eggs and toast" becomes a meal with exact numbers, ready to log in one tap.' },
  { title: 'Training that fits your kit', body: 'Plans built for your goal, schedule and equipment, with last session’s numbers to beat.' },
]

const reduceMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function Arrow() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

function Check() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  )
}

/** The main call to action: leaf-green, with a light tracing its edge. */
function PrimaryCta({ children = 'Open BetterU' }: { children?: string }) {
  return (
    <StarBorder
      as={Link}
      to="/app"
      className="lx-cta-main"
      backgroundColor="#b9e06a"
      textColor="#0a2416"
      color="#ffffff"
      trailColor="#f3f7ee"
      borderColor="rgba(10, 36, 22, 0.25)"
      radius={14}
      duration={5}
      glow={0.6}
      hover="brighten"
    >
      {children} <Arrow />
    </StarBorder>
  )
}

export function Landing() {
  const [answered, setAnswered] = useState(false)
  const typedRef = useRef<HTMLDivElement>(null)
  const still = reduceMotion()

  // TextType only reports completion after deleting a sentence, so watch the
  // typed text and reveal the answer the moment the sentence is complete.
  useEffect(() => {
    if (still) {
      setAnswered(true)
      return
    }
    const el = typedRef.current
    if (!el) return
    const observer = new MutationObserver(() => {
      // Read only the visible typed text (TextType also renders a hidden copy for screen readers).
      const typed = el.querySelector('.text-type__content')?.textContent ?? ''
      if (typed.includes(DEMO.said)) {
        setAnswered(true)
        observer.disconnect()
      }
    })
    observer.observe(el, { subtree: true, childList: true, characterData: true })
    return () => observer.disconnect()
  }, [still])

  return (
    <>
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section className="lx-dark lx-hero">
        <div className="lx-bg" aria-hidden="true">
          <Silk color="#3d9a58" sheenColor="#e2fba6" speed={2.6} scale={1.05} rotation={0.35} sheen={1} depth={0.85} glow={0.6} noiseIntensity={0.7} paused={still} />
        </div>
        <div className="lx-bg-veil" />

        <div className="page-wrap lx-hero-inner">
          <div className="lx-copy">
            <span className="lx-badge"><i /> Built on USDA, WHO and US National Library of Medicine data</span>
            <h1 className="lx-title">Eat with evidence.</h1>
            <p className="lx-lede">
              BetterU tracks what you eat against targets set for your body, builds training around the equipment you have,
              and answers every nutrition question with numbers you can trace back to the source.
            </p>
            <div className="lx-ctas">
              <PrimaryCta />
              <SpecularButton
                size="lg"
                radius={14}
                tint="#12351f"
                tintOpacity={0.35}
                textColor="#f3f7ee"
                lineColor="#b9e06a"
                onClick={() => document.getElementById('how')?.scrollIntoView({ behavior: still ? 'auto' : 'smooth' })}
              >
                See how Alden answers
              </SpecularButton>
            </div>
            <div className="lx-proof">
              <div><strong><CountUp to={13600} separator="," duration={1.6} trigger="load" /></strong><span>foods with real portions</span></div>
              <div><strong><CountUp to={41} duration={1.6} trigger="load" /></strong><span>trusted health guides</span></div>
              <div><strong><CountUp to={876} duration={1.6} trigger="load" /></strong><span>exercises with photos</span></div>
            </div>
          </div>

          <div className="lx-demo" aria-label="Example: Alden reading a breakfast">
            <div className="demo-input" ref={typedRef}>
              <span className="who">You</span>
              <TextType text={DEMO.said} as="span" typingSpeed={34} initialDelay={700} loop={false} showCursor={!answered} cursorCharacter="|" />
            </div>
            <Facts
              title="Nutrition Facts"
              subtitle="Breakfast: 2 large eggs and 1 slice of whole-wheat toast"
              heroLabel="Calories"
              heroValue={<CountUp to={DEMO.kcal} duration={1} startWhen={answered} trigger="load" />}
              rows={DEMO.rows.map((r) => ({
                label: r.label,
                amount: answered ? <><CountUp to={r.grams} decimals={1} duration={1} startWhen={answered} trigger="load" /> g</> : '–',
                share: answered ? r.grams / r.target : 0,
              }))}
              foot={<>Source: USDA FoodData Central, entries <span className="cite">F76</span> and <span className="cite">F10494</span>. {Math.round((DEMO.kcal / DEMO.target) * 100)}% of a 1,650 kcal day.</>}
            >
              <div className="demo-actions">
                <span className="btn btn-accent btn-sm" aria-hidden="true" style={{ opacity: answered ? 1 : 0.4, transition: 'opacity 400ms' }}>Log breakfast</span>
                <span className="small" style={{ alignSelf: 'center', color: '#5f6b62' }}>Saved only when you tap.</span>
              </div>
            </Facts>
          </div>
        </div>

        <div className="lx-sources">
          <LogoLoop
            logos={LOOP.map((name) => ({ node: <span className="lx-source">{name}</span>, title: name }))}
            speed={still ? 0 : 36}
            gap={56}
            logoHeight={22}
            fadeOut
            fadeOutColor="#0a2416"
            pauseOnHover
            ariaLabel="Data sources"
          />
        </div>
      </section>

      {/* ── How Alden answers ────────────────────────────────────── */}
      <section className="lx-section" id="how">
        <div className="page-wrap">
          <ScrollReveal containerClassName="lx-h2" textClassName="lx-reveal-text" baseOpacity={0.12} baseRotation={0} blurStrength={6} stagger={0.06}>
            Every answer is looked up, not made up.
          </ScrollReveal>
          <Reveal as="p" className="lx-sub" delay={100}>Alden is BetterU's coach. Whatever you ask, it follows the same four steps.</Reveal>
          <ol className="lx-steps">
            {STEPS.map((s, i) => (
              <Reveal as="li" key={s.title} className="lx-step" delay={i * 110}>
                <span className="n">{i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      {/* ── The app ──────────────────────────────────────────────── */}
      <section className="lx-section lx-mist">
        <div className="page-wrap lx-show">
          <div>
            <ScrollReveal containerClassName="lx-h2" textClassName="lx-reveal-text" baseOpacity={0.12} baseRotation={0} blurStrength={6} stagger={0.06}>
              Your day, on one label.
            </ScrollReveal>
            <Reveal as="p" className="lx-sub" delay={100}>Built for students, athletes and anyone who wants to eat and train with a plan, on a laptop or a phone.</Reveal>
            <div className="lx-points">
              {POINTS.map((p, i) => (
                <Reveal key={p.title} variant="left" delay={150 + i * 120}><Check /><div><strong>{p.title}</strong><p>{p.body}</p></div></Reveal>
              ))}
            </div>
          </div>
          <Reveal className="lx-phone" variant="scale" delay={150} aria-hidden="true">
            <span className="lx-chip-float lx-chip-a">Alden is looking up <b>chicken breast</b></span>
            <span className="lx-chip-float lx-chip-b">Log lunch, 520 kcal</span>
            <div className="lx-screen">
              <div className="lx-screen-top"><span>Good morning, Nia</span><span style={{ color: '#4e6b12' }}>Today</span></div>
              <Facts
                title="Today"
                subtitle="Target 1,850 kcal to build muscle"
                heroLabel="Calories left"
                heroValue="1,212"
                rows={[
                  { label: 'Eaten', amount: '638 kcal', share: 0.34 },
                  { label: 'Protein', amount: '52 g of 130 g', share: 0.4 },
                  { label: 'Carbohydrate', amount: '71 g of 220 g', share: 0.32 },
                  { label: 'Fat', amount: '18 g of 62 g', share: 0.29 },
                ]}
              />
              <div style={{ background: '#0a2416', color: '#f3f7ee', borderRadius: 10, padding: '12px 14px', fontSize: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <span>78 g of protein to go today.</span>
                <span style={{ background: '#b9e06a', color: '#0a2416', borderRadius: 8, padding: '6px 10px', fontWeight: 700 }}>Get ideas</span>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ── Sources ──────────────────────────────────────────────── */}
      <section className="lx-section">
        <div className="page-wrap">
          <Reveal as="h2" className="lx-h2">Ingredients.</Reveal>
          <Reveal as="p" className="lx-sub" delay={100}>
            Public health data from government and medical sources, a calculator built on the Mifflin–St Jeor equation,
            safety limits on calorie deficits, and your own logs. No influencer advice. No invented numbers.
          </Reveal>
          <div className="lx-sources-list">
            {SOURCES.map((s, i) => (
              <Reveal key={s.name} variant="left" delay={i * 70}><strong>{s.name}</strong><span>{s.what}</span><span className="count">{s.count}</span></Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Founders ─────────────────────────────────────────────── */}
      <section className="lx-dark lx-section" id="founders">
        <div className="page-wrap" style={{ position: 'relative', zIndex: 1 }}>
          <ScrollReveal containerClassName="lx-h2" textClassName="lx-reveal-text" baseOpacity={0.15} baseRotation={0} blurStrength={6} stagger={0.06}>
            Alden is named after the five people who built it.
          </ScrollReveal>
          <Reveal as="p" className="lx-sub" delay={100}>One letter each. A student team turning trusted nutrition science into a coach anyone can use.</Reveal>
          <div className="lx-alden" role="list">
            {FOUNDERS.map((f, i) => (
              <div key={f.name} role="listitem" className={`lx-letter${f.lead ? ' lead' : ''}`}>
                <div className="glyph-mask">
                  <Reveal variant="rise" delay={f.lead ? 640 : i * 120}><span className="glyph" aria-hidden="true">{f.name[0]}</span></Reveal>
                </div>
                <Reveal className="who" delay={(f.lead ? 760 : i * 120 + 120)}>
                  {f.lead && <span className="lx-lead-tag">Project lead</span>}
                  <strong>{f.name}</strong>
                  <span>{f.role}</span>
                </Reveal>
              </div>
            ))}
          </div>
          <p style={{ marginTop: 40 }}><Link to="/team" className="btn btn-sm" style={{ color: 'var(--leaf)', padding: 0, minHeight: 0 }}>Meet the team</Link></p>
        </div>
      </section>

      {/* ── Final call to action ─────────────────────────────────── */}
      <section className="lx-dark lx-section lx-final" style={{ borderTop: '1px solid var(--moss)' }}>
        <div className="lx-bg" aria-hidden="true" style={{ opacity: 0.85 }}>
          <Aurora colorStops={['#1f5a32', '#b9e06a', '#4e6b12']} amplitude={1.1} blend={0.6} speed={0.6} paused={still} />
        </div>
        <div className="page-wrap lx-final-inner">
          <Reveal as="h2" className="lx-h2" style={{ color: 'var(--on-forest)' }}>Start eating with evidence.</Reveal>
          <Reveal as="p" className="lx-sub" delay={120}>Two minutes of setup. Your targets come with the working shown. No account, no sign-up: BetterU remembers this device.</Reveal>
          <Reveal delay={240}><PrimaryCta>Open BetterU, free</PrimaryCta></Reveal>
        </div>
      </section>
    </>
  )
}
