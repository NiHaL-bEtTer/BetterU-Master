// Adapted from the Watermelon UI "Bionis" dashboard sidebar for BetterU.
import { useState } from 'react'
import { Download, ExternalLink, Globe, Settings, Sparkles, Users } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, unwrap } from '@/api/client'
import { useAuth } from '@/auth'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar'
import {
  ArrowRightIcon,
  CloseIcon,
  QuestionIcon,
  SidebarCollapseIcon,
  ToggleIcon,
  UserIcon,
} from '@/components/watermelon/bionis-dashboard/components/bionis/icons'
import { useTheme } from '@/components/watermelon/bionis-dashboard/components/bionis/theme-provider'
import { cn } from '@/lib/utils'
import { NAV_GROUPS, type NavItem } from './nav'

const menuButtonClassName = cn(
  'h-12 gap-2.5 rounded-xl border border-transparent px-3 text-base tracking-tight text-muted-foreground transition-colors',
  'aria-[current=page]:border-border aria-[current=page]:bg-background aria-[current=page]:font-medium aria-[current=page]:text-sidebar-accent-foreground aria-[current=page]:shadow-[1px_2px_12px_rgba(158,158,158,0.08)]',
  'dark:aria-[current=page]:border-transparent dark:aria-[current=page]:bg-sidebar-accent dark:aria-[current=page]:shadow-[1px_2px_12px_rgba(0,0,0,0.25)]',
  'hover:bg-sidebar-accent data-open:bg-background data-open:text-sidebar-accent-foreground dark:data-open:bg-sidebar-accent',
  '[&_svg]:size-5!',
  'group-data-[collapsible=icon]:size-11! group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0! group-data-[collapsible=icon]:[&>span]:hidden',
)

export function useActiveNav(pathname: string) {
  return (item: NavItem) => (item.href === '/app' ? pathname === '/app' || pathname === '/app/' : pathname.startsWith(item.href))
}

function NavItemButton({ item }: { item: NavItem }) {
  const { isMobile, setOpenMobile } = useSidebar()
  const { pathname } = useLocation()
  const active = useActiveNav(pathname)(item)
  return (
    <SidebarMenuButton asChild isActive={active} tooltip={item.name} className={menuButtonClassName}>
      <Link to={item.href} aria-current={active ? 'page' : undefined} onClick={() => isMobile && setOpenMobile(false)}>
        <item.icon />
        <span>{item.name}</span>
      </Link>
    </SidebarMenuButton>
  )
}

function HelpItem() {
  return (
    <SidebarMenuItem>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton tooltip="Help" className={menuButtonClassName}>
            <QuestionIcon />
            <span>Help</span>
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="top" align="start" className="bionis-dashboard betteru w-60">
          <DropdownMenuLabel className="font-normal">
            <p className="text-sm font-medium text-foreground">Need help?</p>
            <p className="text-muted-foreground">How BetterU works and where its numbers come from.</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem asChild><Link to="/#how"><Sparkles />How Alden answers</Link></DropdownMenuItem>
            <DropdownMenuItem asChild><Link to="/team"><Users />Meet the founders</Link></DropdownMenuItem>
            <DropdownMenuItem asChild><Link to="/"><Globe />BetterU website</Link></DropdownMenuItem>
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  )
}

function DarkModeItem() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const label = isDark ? 'Light mode' : 'Dark mode'
  return (
    <SidebarMenuItem>
      <SidebarMenuButton tooltip={label} className={menuButtonClassName} onClick={() => setTheme(isDark ? 'light' : 'dark')}>
        <ToggleIcon pressed={isDark} />
        <span>{label}</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

async function downloadData() {
  const data = await unwrap(api.GET('/api/profile/export'))
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
  Object.assign(document.createElement('a'), { href: url, download: 'betteru-data.json' }).click()
  URL.revokeObjectURL(url)
}

function ProfileItem() {
  const { user } = useAuth()
  const navigate = useNavigate()
  return (
    <SidebarMenuItem>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <SidebarMenuButton tooltip="Profile" className={menuButtonClassName}>
            <UserIcon />
            <span>Profile</span>
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="top" align="start" className="bionis-dashboard betteru w-60">
          <DropdownMenuLabel className="font-normal">
            <p className="text-sm font-medium text-foreground">{user?.name || 'Your profile'}</p>
            <p className="text-muted-foreground">Saved on this device</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem onSelect={() => navigate('/app/me')}><Settings />Profile and targets</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => { void downloadData() }}><Download />Download my data</DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild><Link to="/"><ExternalLink />Back to website</Link></DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  )
}

function CollapseControl({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  if (!collapsed) {
    return (
      <button type="button" onClick={onToggle} className="flex size-9.5 shrink-0 items-center justify-center rounded-lg transition-colors hover:bg-sidebar-accent" aria-label="Collapse sidebar">
        <SidebarCollapseIcon className="-rotate-90" />
      </button>
    )
  }
  return (
    <div className="group/collapse relative size-11 shrink-0">
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-(--bionis-blue) transition-all ease-linear group-hover/collapse:scale-75 group-hover/collapse:opacity-0">
        <Logo size={22} />
      </div>
      <div className="pointer-events-none absolute inset-0 flex scale-75 items-center justify-center opacity-0 transition-all ease-linear group-hover/collapse:pointer-events-auto group-hover/collapse:scale-100 group-hover/collapse:opacity-100">
        <button type="button" onClick={onToggle} className="flex size-11 items-center justify-center rounded-lg transition-colors hover:bg-sidebar-accent" aria-label="Expand sidebar">
          <SidebarCollapseIcon className="rotate-90" />
        </button>
      </div>
    </div>
  )
}

function CoachCard() {
  const [open, setOpen] = useState(true)
  const navigate = useNavigate()
  const { isMobile, setOpenMobile } = useSidebar()
  if (!open) return null
  return (
    <div className={cn('coach-card relative flex flex-col gap-8 rounded-2xl border p-4', 'bg-[linear-gradient(347deg,var(--promo-gradient-from)_47.58%,var(--promo-gradient-to)_306.43%)]', 'group-data-[collapsible=icon]:hidden')}>
      <div className="flex items-start justify-between gap-2">
        <span className="rounded-xl bg-primary px-2.5 py-1.5 text-xs font-medium tracking-tight text-primary-foreground">Coach</span>
        <button type="button" onClick={() => setOpen(false)} className="flex size-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground" aria-label="Hide the Alden card">
          <CloseIcon className="size-4" />
        </button>
      </div>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <p className="font-semibold tracking-tight">Ask Alden</p>
          <p className="text-sm tracking-tight text-muted-foreground">Exact nutrition, meal logging and plans, with sources.</p>
        </div>
        <Button type="button" className="h-11 w-full gap-1 rounded-xl pr-2 pl-3 text-sm tracking-tight" onClick={() => { navigate('/app/alden'); if (isMobile) setOpenMobile(false) }}>
          Open chat
          <ArrowRightIcon className="size-5" />
        </Button>
      </div>
    </div>
  )
}

export function ShellSidebar() {
  const { state, toggleSidebar } = useSidebar()
  const collapsed = state === 'collapsed'
  return (
    <Sidebar collapsible="icon" className="h-full border-none">
      <SidebarHeader className={cn('h-16 flex-row items-center border-b border-sidebar-border transition-[padding] md:h-20', collapsed ? 'justify-start px-3' : 'justify-between gap-4.75 px-4')}>
        {!collapsed && (
          <Link to="/app" className="flex min-w-0 flex-1 items-center gap-2 text-(--bionis-blue)">
            <Logo size={22} />
            <span className="truncate text-xl font-semibold tracking-tight text-sidebar-foreground">BetterU</span>
          </Link>
        )}
        <CollapseControl collapsed={collapsed} onToggle={toggleSidebar} />
      </SidebarHeader>

      <SidebarContent className="gap-4 overflow-x-hidden overflow-y-auto px-3 py-4 group-data-[collapsible=icon]:overflow-y-auto!">
        {NAV_GROUPS.map((group) => (
          <SidebarGroup key={group.label} className="gap-2 p-0">
            <SidebarGroupLabel className="h-auto px-3 py-1 text-base font-normal tracking-tight text-muted-foreground">{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu className="gap-2">
                {group.items.map((item) => (
                  <SidebarMenuItem key={item.href}><NavItemButton item={item} /></SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="gap-6 border-t border-sidebar-border px-3 py-3">
        <CoachCard />
        <SidebarMenu className="gap-2">
          <HelpItem />
          <DarkModeItem />
          <ProfileItem />
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
