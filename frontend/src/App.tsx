import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { BottomNav } from './components/BottomNav'
import { AccountPage } from './pages/AccountPage'
import { HomePage } from './pages/HomePage'
import { MapPage } from './pages/MapPage'
import { MatchesPage } from './pages/MatchesPage'
import { PickupLandingPage, PickupPage } from './pages/PickupPage'
import { ReportPage } from './pages/ReportPage'

function Shell() {
  return (
    <div className="mx-auto min-h-dvh w-full max-w-md px-4 pb-28 pt-4">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/account" element={<AccountPage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/matches" element={<MatchesPage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/pickup" element={<PickupLandingPage />} />
        <Route path="/pickup/:lostId/:foundId" element={<PickupPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <BottomNav />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  )
}
