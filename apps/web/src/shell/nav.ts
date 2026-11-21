import { Dumbbell, LayoutDashboard, LineChart, MessageCircle, UtensilsCrossed, type LucideIcon } from 'lucide-react'

export type NavItem = { name: string; href: string; icon: LucideIcon; hint: string }
export type NavGroup = { label: string; items: NavItem[] }

export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Overview',
    items: [
      { name: 'Today', href: '/app', icon: LayoutDashboard, hint: 'Your day at a glance' },
      { name: 'Food log', href: '/app/log', icon: UtensilsCrossed, hint: 'Everything you ate' },
      { name: 'Alden', href: '/app/alden', icon: MessageCircle, hint: 'Your nutrition coach' },
    ],
  },
  {
    label: 'Training',
    items: [
      { name: 'Train', href: '/app/train', icon: Dumbbell, hint: 'Your workout plan' },
      { name: 'Progress', href: '/app/progress', icon: LineChart, hint: 'Weight trend and maintenance' },
    ],
  },
]

export const ALL_NAV = NAV_GROUPS.flatMap((g) => g.items)
