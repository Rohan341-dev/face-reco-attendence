import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/layout/AppShell'
import { AuthProvider, useAuth } from '@/lib/auth'
import { AttendancePage } from '@/pages/AttendancePage'
import { DashboardPage } from '@/pages/DashboardPage'
import { DevicesPage } from '@/pages/DevicesPage'
import { LoginPage } from '@/pages/LoginPage'
import { MfaPage } from '@/pages/MfaPage'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { PeoplePage } from '@/pages/PeoplePage'
import { SchedulesPage } from '@/pages/SchedulesPage'
import { SettingsPage } from '@/pages/SettingsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 15_000, retry: 1, refetchOnWindowFocus: false },
  },
})

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { authenticated, ready } = useAuth()
  if (!ready) return <div className="grid min-h-screen place-items-center text-sm text-muted">Loading…</div>
  if (!authenticated) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/mfa" element={<MfaPage />} />
            <Route path="/onboard" element={<OnboardingPage />} />
            <Route element={<RequireAuth><AppShell /></RequireAuth>}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/attendance" element={<AttendancePage />} />
              <Route path="/people" element={<PeoplePage />} />
              <Route path="/schedules" element={<SchedulesPage />} />
              <Route path="/devices" element={<DevicesPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
