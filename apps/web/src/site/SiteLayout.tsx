import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Brand } from '../components/Logo'

export function SiteLayout() {
  const [scrolled, setScrolled] = useState(false)
  const [overDark, setOverDark] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const { pathname, hash } = useLocation()

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 8)
      // Keep the nav dark while it sits over the dark hero.
      const hero = document.querySelector<HTMLElement>('.lx-hero')
      setOverDark(!!hero && window.scrollY < hero.offsetHeight - 72)
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [pathname])

  // New page: start at the top (or at the #section that was linked).
  useEffect(() => {
    setMenuOpen(false)
    if (hash) document.querySelector(hash)?.scrollIntoView()
    else window.scrollTo(0, 0)
  }, [pathname, hash])

  return (
    <div className="site">
      <header className={`site-nav${scrolled ? ' scrolled' : ''}${pathname === '/' && (overDark || !scrolled) && !menuOpen ? ' on-dark' : ''}`}>
        <Brand />
        <nav className="site-links" aria-label="Website">
          <Link to="/#how">How it works</Link>
          <NavLink to="/about">About</NavLink>
          <NavLink to="/team">Founders</NavLink>
        </nav>
        <div className="row" style={{ gap: 6 }}>
          <Link className="btn btn-primary btn-sm" to="/app">Open BetterU</Link>
          <button className="icon-btn site-menu-btn" aria-expanded={menuOpen} aria-label="Menu" onClick={() => setMenuOpen((o) => !o)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              {menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 8h16M4 16h16" />}
            </svg>
          </button>
        </div>
      </header>
      {menuOpen && (
        <nav className="site-menu" aria-label="Website">
          <Link to="/#how">How it works</Link>
          <Link to="/about">About</Link>
          <Link to="/team">Founders</Link>
        </nav>
      )}
      <main className="site-main">
        <Outlet />
      </main>
      <footer className="site-foot lx-foot">
        <div className="page-wrap">
          <span>BetterU gives general guidance, not medical advice. Made by Aishat, Lashe, Dana, Elizabeth and Nihal.</span>
          <nav aria-label="Footer">
            <Link to="/about">About</Link>
            <Link to="/team">Founders</Link>
            <Link to="/app">Open BetterU</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
