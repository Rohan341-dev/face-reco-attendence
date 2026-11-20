import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Activity,
  CalendarDays,
  ChevronLeft,
  Cpu,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  Users,
} from 'lucide-react'
import { useState } from 'react'

import { Badge, Button } from '@/components/ui'
import { useAuth } from '@/lib/auth'
import { useCurrentOrg } from '@/lib/api/queries'
import { cn } from '@/lib/utils'

const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/attendance', label: 'Attendance', icon: Activity },
  { to: '/people', label: 'People', icon: Users },
  { to: '/schedules', label: 'Schedules', icon: CalendarDays },
  { to: '/devices', label: 'Devices', icon: Cpu },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function AppShell() {
  const [open, setOpen] = useState(false)
  const { signOut, me } = useAuth()
  const org = useCurrentOrg()
  const navigate = useNavigate()

  const logout = () => {
    signOut()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen bg-canvas">
      {open && <button aria-label="Close navigation" className="fixed inset-0 z-30 bg-slate-950/70 lg:hidden" onClick={() => setOpen(false)} />}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-surface transition-transform lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-line px-5">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/15 text-accent">
              <Activity size={18} />
            </span>
            <div>
              <p className="text-sm font-semibold tracking-tight">FaceTrack AI</p>
              <p className="text-[11px] text-muted">Attendance platform</p>
            </div>
          </div>
          <button className="text-muted lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu">
            <ChevronLeft size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-5">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                  isActive ? 'bg-accent/10 text-emerald-300' : 'text-muted hover:bg-surface-2 hover:text-slate-100',
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-line p-3">
          <div className="rounded-lg bg-surface-2 p-3">
            <p className="truncate text-xs font-medium text-slate-200">{org.data?.name ?? 'Loading organization…'}</p>
            <p className="mt-0.5 truncate text-[11px] text-muted">{me?.email ?? ''}</p>
            <div className="mt-2 flex items-center gap-2">
              <Badge tone="info">{me?.is_platform_admin ? 'Platform admin' : 'Organization'}</Badge>
              <Button variant="ghost" size="icon" className="ml-auto" onClick={logout} aria-label="Sign out">
                <LogOut size={16} />
              </Button>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-canvas/90 px-4 backdrop-blur lg:px-8">
          <button className="text-muted lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <div className="ml-auto flex items-center gap-3">
            <span className="hidden text-xs text-muted sm:block">Secure session · JWT</span>
            <span className="h-2 w-2 rounded-full bg-accent" title="Services online" />
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-7 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
