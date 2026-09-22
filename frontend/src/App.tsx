import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation, useSearchParams } from 'react-router-dom'
import { AlertsProvider } from './auth/AlertsContext'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { RedirectToLogin } from './auth/RedirectToLogin'
import { BottomNav } from './components/BottomNav'
import { TopBar } from './components/TopBar'
import { AccountPage } from './pages/AccountPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { MapPage } from './pages/MapPage'
import { PickupLandingPage, PickupPage } from './pages/PickupPage'
import { ReportDetailPage } from './pages/ReportDetailPage'
import { ReportPage } from './pages/ReportPage'
import { ReportsPage } from './pages/ReportsPage'

function MatchesRedirect() {
  const [params] = useSearchParams()
  const id = params.get('report')
  return <Navigate to={id ? `/reports/${encodeURIComponent(id)}` : '/reports'} replace />
}

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function Shell() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="mx-auto min-h-dvh w-full max-w-md px-4 pt-16">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="mx-auto min-h-dvh w-full max-w-md px-4 pb-8">
        <main>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<LoginPage />} />
            <Route path="*" element={<RedirectToLogin />} />
          </Routes>
        </main>
      </div>
    )
  }

  return (
    <div className="mx-auto min-h-dvh w-full max-w-md px-4 pb-28">
      <TopBar />
      <main className="pt-4">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/reports/:id/edit" element={<ReportPage />} />
          <Route path="/reports/:id" element={<ReportDetailPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/matches" element={<MatchesRedirect />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/around" element={<Navigate to="/map" replace />} />
          <Route path="/pickup" element={<PickupLandingPage />} />
          <Route path="/pickup/:lostId/:foundId" element={<PickupPage />} />
          <Route path="/login" element={<Navigate to="/" replace />} />
          <Route path="/register" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AlertsProvider>
          <ScrollToTop />
          <Shell />
        </AlertsProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
