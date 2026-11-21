import { lazy, Suspense, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import { SiteLayout } from './site/SiteLayout'

// Screens load on demand: website visitors don't download the app, and vice versa.
const AppRoot = lazy(() => import('./AppRoot').then((m) => ({ default: m.AppRoot })))
const Layout = lazy(() => import('./shell/AppShell').then((m) => ({ default: m.AppShell })))
const Landing = lazy(() => import('./site/Landing').then((m) => ({ default: m.Landing })))
const Alden = lazy(() => import('./pages/Alden').then((m) => ({ default: m.Alden })))
const Log = lazy(() => import('./pages/Log').then((m) => ({ default: m.Log })))
const Me = lazy(() => import('./pages/Me').then((m) => ({ default: m.Me })))
const Onboarding = lazy(() => import('./pages/Onboarding').then((m) => ({ default: m.Onboarding })))
const Progress = lazy(() => import('./pages/Progress').then((m) => ({ default: m.Progress })))
const Today = lazy(() => import('./pages/Today').then((m) => ({ default: m.Today })))
const Train = lazy(() => import('./pages/Train').then((m) => ({ default: m.Train })))
const About = lazy(() => import('./site/About').then((m) => ({ default: m.About })))
const Team = lazy(() => import('./site/Team').then((m) => ({ default: m.Team })))

function Ready({ children, needsProfile = true }: { children: ReactNode; needsProfile?: boolean }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center-page"><div className="skeleton" style={{ width: 180, height: 14 }} /></div>
  if (!user) {
    return (
      <div className="center-page">
        <div className="stack" style={{ maxWidth: 380 }}>
          <h1>BetterU can't reach its server</h1>
          <p className="muted">Check that the BetterU server is running, then try again.</p>
          <button className="btn btn-primary" onClick={() => location.reload()}>Try again</button>
        </div>
      </div>
    )
  }
  if (needsProfile && !user.has_profile) return <Navigate to="/app/onboarding" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="center-page"><div className="skeleton" style={{ width: 180, height: 14 }} /></div>}>
      <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<Landing />} />
          <Route path="about" element={<About />} />
          <Route path="team" element={<Team />} />
        </Route>
        <Route path="app" element={<AppRoot />}>
          <Route path="onboarding" element={<Ready needsProfile={false}><Onboarding /></Ready>} />
          <Route element={<Ready><Layout /></Ready>}>
            <Route index element={<Today />} />
            <Route path="log" element={<Log />} />
            <Route path="alden" element={<Alden />} />
            <Route path="train" element={<Train />} />
            <Route path="progress" element={<Progress />} />
            <Route path="me" element={<Me />} />
          </Route>
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
