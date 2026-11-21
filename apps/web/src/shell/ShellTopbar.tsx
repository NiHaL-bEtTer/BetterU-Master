// Adapted from the Watermelon UI "Bionis" dashboard top bar for BetterU.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Check, Download, Monitor, Moon, Settings, Scale, Sun, UtensilsCrossed } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, todayISO, unwrap, type DaySummary, type ProfileInput } from '@/api/client'
import { useAuth } from '@/auth'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { BellIcon, CloseIcon, SearchIcon } from '@/components/watermelon/bionis-dashboard/components/bionis/icons'
import { useTheme, type Theme } from '@/components/watermelon/bionis-dashboard/components/bionis/theme-provider'
import { cn } from '@/lib/utils'
import { ALL_NAV } from './nav'
import { useActiveNav } from './ShellSidebar'

const GOAL_LABEL: Record<string, string> = { cut: 'Losing fat', maintain: 'Maintaining', bulk: 'Building muscle' }

type Note = { id: string; title: string; description: string; to: string; icon: typeof Scale; tone: string }

function useNotes(day: DaySummary | null, weighedToday: boolean): Note[] {
  const notes: Note[] = []
  if (day && day.entries.length === 0) {
    notes.push({ id: 'log', title: 'Nothing logged yet today', description: 'Tell Alden what you ate, or add it in the food log.', to: '/app/log', icon: UtensilsCrossed, tone: 'bg-(--bionis-blue)/10 text-(--bionis-blue)' })
  }
  if (day?.targets) {
    const left = Math.round(day.targets.macros.protein_g - day.totals.protein_g)
    if (day.entries.length > 0 && left > 30) {
      notes.push({ id: 'protein', title: `${left} g of protein to go`, description: 'Ask Alden for high-protein ideas that fit your calories.', to: `/app/alden?q=${encodeURIComponent(`Give me 3 high-protein snack ideas with about ${Math.min(left, 40)} g protein`)}`, icon: UtensilsCrossed, tone: 'bg-(--metric-protein)/10 text-(--metric-protein)' })
    }
  }
  if (!weighedToday) {
    notes.push({ id: 'weigh', title: 'Morning weigh-in', description: 'A daily weight keeps your trend and maintenance estimate accurate.', to: '/app/progress', icon: Scale, tone: 'bg-(--metric-fat)/10 text-(--metric-fat)' })
  }
  return notes
}

function ThemeMenu() {
  const { theme, resolvedTheme, setTheme } = useTheme()
  const options: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'Match device', icon: Monitor },
  ]
  const Current = resolvedTheme === 'dark' ? Moon : Sun
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" size="icon-lg" className="size-11" aria-label={`Theme: ${theme === 'system' ? 'match device' : theme}`}>
          <Current className="size-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="bionis-dashboard betteru w-44">
        {options.map((o) => (
          <DropdownMenuItem key={o.value} onSelect={() => setTheme(o.value)} className="gap-2">
            <o.icon className="size-4" />
            <span className="flex-1">{o.label}</span>
            {theme === o.value && <Check className="size-4 text-(--bionis-blue)" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function ShellTopbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isActive = useActiveNav(pathname)
  const current = ALL_NAV.find(isActive) ?? (pathname.startsWith('/app/me') ? { name: 'Profile', icon: Settings } : ALL_NAV[0])
  const PageIcon = current.icon
  const [query, setQuery] = useState('')
  const [mobileSearch, setMobileSearch] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const mobileRef = useRef<HTMLInputElement>(null)
  const [profile, setProfile] = useState<ProfileInput | null>(null)
  const [day, setDay] = useState<DaySummary | null>(null)
  const [weighedToday, setWeighedToday] = useState(true)

  useEffect(() => {
    unwrap(api.GET('/api/profile')).then((d) => setProfile(d.profile)).catch(() => {})
    unwrap(api.GET('/api/log/{day}', { params: { path: { day: todayISO() } } })).then(setDay).catch(() => {})
    unwrap(api.GET('/api/progress')).then((p) => setWeighedToday(p.weights.at(-1)?.date === todayISO())).catch(() => {})
  }, [pathname])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        if (window.matchMedia('(width < 48rem)').matches) {
          setMobileSearch(true)
          requestAnimationFrame(() => mobileRef.current?.focus())
        } else inputRef.current?.focus()
      }
      if (e.key === 'Escape') setMobileSearch(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const notes = useNotes(day, weighedToday)

  function search(e: FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    setMobileSearch(false)
    setQuery('')
    navigate(`/app/log?q=${encodeURIComponent(q)}`)
  }

  const name = user?.name?.trim() || 'You'
  const searchField = (ref: typeof inputRef, className: string) => (
    <form onSubmit={search} className={className} role="search">
      <InputGroup className="h-11 w-full border-none bg-secondary py-1 pr-2 pl-3">
        <InputGroupAddon className="pl-0 text-muted-foreground"><SearchIcon /></InputGroupAddon>
        <InputGroupInput ref={ref} className="h-full px-1.5! text-sm tracking-tight placeholder:text-muted-foreground" aria-label="Search foods" placeholder="search foods to log..." value={query} onChange={(e) => setQuery(e.target.value)} />
        <InputGroupAddon align="inline-end" className="hidden pr-1 text-xs text-muted-foreground lg:flex">⌘K</InputGroupAddon>
      </InputGroup>
    </form>
  )

  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-3 border-b px-4 py-4 md:h-20 md:pr-8 md:pl-6">
      {mobileSearch ? (
        <div className="flex w-full items-center gap-2 md:hidden">
          {searchField(mobileRef, 'flex-1')}
          <Button type="button" variant="outline" size="icon-lg" className="size-11 shrink-0" aria-label="Close search" onClick={() => setMobileSearch(false)}>
            <CloseIcon />
          </Button>
        </div>
      ) : (
        <>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <SidebarTrigger className="size-11 shrink-0 md:hidden [&_svg]:size-5!" />
            <div className="flex items-center gap-3">
              <PageIcon className="hidden size-5 shrink-0 md:block" />
              <p className="truncate text-lg font-medium">{current.name}</p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {searchField(inputRef, 'hidden w-70 md:block')}
            <Button type="button" variant="outline" size="icon-lg" className="size-11 rounded-lg md:hidden" aria-label="Search foods" onClick={() => { setMobileSearch(true); requestAnimationFrame(() => mobileRef.current?.focus()) }}>
              <SearchIcon className="size-4" />
            </Button>

            <ThemeMenu />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button type="button" variant="outline" size="icon-lg" className="relative size-11" aria-label={`Notifications${notes.length ? `, ${notes.length} new` : ''}`}>
                  <BellIcon className="size-6!" />
                  {notes.length ? (
                    <svg aria-hidden viewBox="0 0 10 10" className="pointer-events-none absolute top-2 right-2 size-2.5 overflow-visible">
                      <circle cx="5" cy="5" r="5" className="fill-background" />
                      <circle cx="5" cy="5" r="2.75" fill="none" className="stroke-destructive" strokeWidth="2" />
                    </svg>
                  ) : null}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bionis-dashboard betteru ml-3 w-80 p-0">
                <div className="flex items-center justify-between gap-3 border-b px-3.5 py-3">
                  <p className="text-sm font-medium">Today</p>
                  <p className="text-xs text-muted-foreground">{notes.length ? `${notes.length} to do` : 'All caught up'}</p>
                </div>
                <div className="p-1.5">
                  {notes.length === 0 && <p className="px-2.5 py-4 text-center text-sm text-muted-foreground">Nothing needs your attention right now.</p>}
                  {notes.map((n) => (
                    <DropdownMenuItem key={n.id} className="cursor-pointer items-start gap-3 rounded-xl px-2.5 py-2.5 [&_svg]:!text-inherit" onSelect={() => navigate(n.to)}>
                      <span className={cn('mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg', n.tone)}><n.icon className="size-4" /></span>
                      <div className="min-w-0 flex-1 space-y-1">
                        <p className="text-sm leading-snug font-medium">{n.title}</p>
                        <p className="text-xs leading-relaxed text-muted-foreground">{n.description}</p>
                      </div>
                    </DropdownMenuItem>
                  ))}
                </div>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button type="button" variant="ghost" className="h-auto gap-2 px-0 hover:bg-transparent aria-expanded:bg-transparent" aria-label="Your profile">
                  <span className="flex size-11 items-center justify-center rounded-lg bg-(--brand-forest) text-lg font-semibold text-(--brand-leaf)">{name[0].toUpperCase()}</span>
                  <div className="hidden flex-col items-start gap-1 text-left md:flex">
                    <span className="text-base leading-none font-medium">{name}</span>
                    <span className="flex items-center gap-1.5 text-sm leading-none text-muted-foreground">
                      {profile ? `Age: ${profile.age}` : 'Your plan'}
                      <span aria-hidden className="block size-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
                      <span className="text-(--live)">{profile ? GOAL_LABEL[profile.goal] : 'Set up'}</span>
                    </span>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bionis-dashboard betteru w-64">
                <div className="space-y-1 px-2 py-2">
                  <p className="text-sm font-medium">{name}</p>
                  {profile && <p className="text-xs text-muted-foreground">{profile.height_cm.toFixed(0)} cm, {profile.weight_kg.toFixed(1)} kg, trains {profile.training_days} days a week</p>}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild><Link to="/app/me"><Settings />Profile and targets</Link></DropdownMenuItem>
                <DropdownMenuItem asChild><Link to="/app/progress"><Scale />Log today's weight</Link></DropdownMenuItem>
                <DropdownMenuItem onSelect={() => { void unwrap(api.GET('/api/profile/export')).then((data) => { const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })); Object.assign(document.createElement('a'), { href: url, download: 'betteru-data.json' }).click(); URL.revokeObjectURL(url) }) }}><Download />Download my data</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </>
      )}
    </header>
  )
}
