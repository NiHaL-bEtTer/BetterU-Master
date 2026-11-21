import type { CSSProperties } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { SidebarProvider } from '@/components/ui/sidebar'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ThemeProvider } from '@/components/watermelon/bionis-dashboard/components/bionis/theme-provider'
import '@/components/watermelon/bionis-dashboard/dashboard.css'
import './theme.css'
import { ShellSidebar } from './ShellSidebar'
import { ShellTopbar } from './ShellTopbar'

/** The app frame, built on the Watermelon UI "Bionis" dashboard layout. */
export function AppShell() {
  const { pathname } = useLocation()
  return (
    <ThemeProvider storageKey="betteru-theme" defaultTheme="system">
      <TooltipProvider delayDuration={300}>
        <SidebarProvider
          defaultOpen
          className="bionis-dashboard betteru no-scrollbar h-svh overflow-hidden"
          style={{ '--sidebar-width': '18.125rem', '--sidebar-width-icon': '4.25rem' } as CSSProperties}
        >
          <ShellSidebar />
          <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <ShellTopbar />
            <div key={pathname} className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-10">
              <Outlet />
            </div>
          </main>
        </SidebarProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}
