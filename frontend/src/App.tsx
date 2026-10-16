import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ResearchProvider } from './context/ResearchContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Layout } from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Portfolio from './pages/Portfolio'
import News from './pages/News'
import ValuationLab from './pages/ValuationLab'
import PseValuationsV2 from './pages/PseValuationsV2'
import UsRefreshControl from './pages/UsRefreshControl'
import UsValuations from './pages/UsValuations'
import AiInsights from './pages/AiInsights'

const Walkthrough = lazy(() => import('./pages/Walkthrough'))

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ResearchProvider>
          <Routes>
            <Route path="/" element={<Suspense fallback={<main style={{ padding: '12vh 8vw' }}><h1>FinSight</h1><p>Filing-based company research.</p><a href="/valuation/AAPL">Continue to FinSight →</a></main>}><Walkthrough /></Suspense>} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route path="/valuation" element={<Navigate to="/valuation/AAPL" replace />} />
              <Route path="/valuation/:ticker" element={<UsValuations />} />
              <Route path="/news" element={<News />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/ai-insights" element={<AiInsights />} />
              <Route path="/pse" element={<Navigate to="/pse/AP" replace />} />
              <Route path="/pse/:ticker" element={<PseValuationsV2 />} />
              <Route path="/pse-v2" element={<Navigate to="/pse/AP" replace />} />
              <Route path="/pse-legacy" element={<ValuationLab />} />
              <Route path="/us-refresh" element={<UsRefreshControl />} />
              <Route path="/us-valuations" element={<Navigate to="/valuation/AAPL" replace />} />
              <Route path="/health" element={<Navigate to="/valuation/AAPL" replace />} />
              <Route path="/rankings" element={<Navigate to="/valuation/AAPL" replace />} />
              <Route path="/companies" element={<Navigate to="/valuation/AAPL" replace />} />
              <Route path="/value" element={<Navigate to="/pse/AP" replace />} />
              <Route path="/brief" element={<Navigate to="/ai-insights" replace />} />
              <Route path="/saved" element={<Navigate to="/portfolio?tab=saved" replace />} />
            </Route>
            <Route path="*" element={<Navigate to="/valuation/AAPL" replace />} />
          </Routes>
        </ResearchProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
