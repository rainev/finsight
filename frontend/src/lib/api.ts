// Thin API client for the valuation backend.
//
// The access token is kept in memory (not localStorage) so it can't be lifted
// from disk by XSS. The refresh token lives in an httpOnly cookie the browser
// sends automatically because every request uses `credentials: 'include'`.

import type {
  AuthResponse,
  Company,
  FeedInsight,
  HealthResponse,
  Holding,
  NewsArticle,
  PseCalculatorResult,
  PseCalculatorView,
  PseValuation,
  PseValuationHistory,
  PseValuationList,
  PublicUser,
  RankingsResponse,
  ResearchCompany,
  ResearchValuation,
  SavedValuation,
  Sentiment,
  SmartBrief,
  UsValuation,
  UsCalculatorResult,
  UsCalculatorView,
  UsValuationList,
  UsValuationHistory,
  UsRefreshControlStatus,
  ValuationResult,
} from './types'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:4001'

let accessToken: string | null = null
export function setAccessToken(token: string | null) {
  accessToken = token
}

interface RequestOpts extends RequestInit {
  _retried?: boolean
}

async function request<T>(path: string, options: RequestOpts = {}): Promise<T> {
  const res = await fetch(`${BASE}/api${path}`, {
    ...options,
    credentials: 'include', // send/receive the refresh cookie
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  })

  // Access token expired mid-session: silently refresh once, then retry.
  if (res.status === 401 && !options._retried && !path.startsWith('/auth/')) {
    try {
      await refresh()
      return request<T>(path, { ...options, _retried: true })
    } catch {
      // fall through to the error below
    }
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error((data as { error?: string } | null)?.error ?? 'Request failed')
  }
  return data as T
}

// --- Auth ---
export async function register(email: string, password: string): Promise<PublicUser> {
  const data = await request<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  setAccessToken(data.access_token)
  return data.user
}

export async function login(email: string, password: string): Promise<PublicUser> {
  const data = await request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
  setAccessToken(data.access_token)
  return data.user
}

// Sign in / register with Google: sends the ID token from Google Identity
// Services; the backend verifies it and finds-or-creates the account.
export async function google(credential: string): Promise<PublicUser> {
  const data = await request<AuthResponse>('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  })
  setAccessToken(data.access_token)
  return data.user
}

export async function refresh(): Promise<PublicUser> {
  const data = await request<AuthResponse>('/auth/refresh', { method: 'POST' })
  setAccessToken(data.access_token)
  return data.user
}

export async function logout(): Promise<void> {
  await request<null>('/auth/logout', { method: 'POST' })
  setAccessToken(null)
}

// --- Companies ---
export function listCompanies(filters?: { sector?: string; market?: string; q?: string }): Promise<Company[]> {
  const params = new URLSearchParams()
  if (filters?.sector) params.set('sector', filters.sector)
  if (filters?.market) params.set('market', filters.market)
  if (filters?.q) params.set('q', filters.q)
  const query = params.size ? `?${params}` : ''
  return request<Company[]>(`/companies${query}`)
}

// --- Valuations ---
export function runValuation(model: string, payload: unknown): Promise<ValuationResult> {
  return request<ValuationResult>(`/valuations/${model}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listValuations(): Promise<SavedValuation[]> {
  return request<SavedValuation[]>('/valuations')
}

export function deleteValuation(id: number): Promise<null> {
  return request<null>(`/valuations/${id}`, { method: 'DELETE' })
}

// --- Holdings (portfolio) ---
export function listHoldings(): Promise<Holding[]> {
  return request<Holding[]>('/holdings')
}

export function addHolding(ticker: string, market = 'US'): Promise<Holding> {
  return request<Holding>('/holdings', {
    method: 'POST',
    body: JSON.stringify({ ticker, market }),
  })
}

export function removeHolding(id: number): Promise<null> {
  return request<null>(`/holdings/${id}`, { method: 'DELETE' })
}

// --- Insights feed (holdings-scoped) ---
export function listInsights(limit = 50): Promise<FeedInsight[]> {
  return request<FeedInsight[]>(`/insights?limit=${limit}`)
}

// --- News feed (raw market news) ---
export function listNews(limit = 50): Promise<NewsArticle[]> {
  return request<NewsArticle[]>(`/news?limit=${limit}`)
}

// Force a fresh pull from GNews (admin-only on the backend).
export function refreshNews(): Promise<{ ingested: number }> {
  return request<{ ingested: number }>('/news/refresh', { method: 'POST' })
}

// --- Research workbench (filing-based) ---
export function listResearchCompanies(): Promise<ResearchCompany[]> {
  return request<ResearchCompany[]>('/research/companies')
}

export function getRankings(risk: number): Promise<RankingsResponse> {
  return request<RankingsResponse>(`/research/rankings?risk=${risk}`)
}

export function getHealth(ticker: string, risk: number): Promise<HealthResponse> {
  return request<HealthResponse>(`/research/health/${ticker}?risk=${risk}`)
}

export function getValuation(ticker: string, sentiment: Sentiment): Promise<ResearchValuation> {
  return request<ResearchValuation>(`/research/valuation/${ticker}?sentiment=${sentiment}`)
}

export function getBrief(ticker: string, risk: number, sentiment: Sentiment): Promise<SmartBrief> {
  return request<SmartBrief>(`/research/brief/${ticker}?risk=${risk}&sentiment=${sentiment}`)
}

// --- Governed PSE V2 catalog ---
export function listPseValuations(): Promise<PseValuationList> {
  return request<PseValuationList>('/pse-valuations')
}

export function getUsRefreshControl(): Promise<UsRefreshControlStatus> {
  return request<UsRefreshControlStatus>('/us-refresh-control/status')
}

export function startUsStagedRefresh(): Promise<{ id: number; status: 'queued'; requested_at: string }> {
  return request('/us-refresh-control/run', { method: 'POST' })
}

export function startUsManualRefresh(): Promise<{ id: number; status: 'queued'; requested_at: string }> {
  return request('/us-refresh-control/run-now', { method: 'POST' })
}

export function inviteUsRefreshUser(email: string): Promise<{ user_id: number; email: string; granted_at: string }> {
  return request('/us-refresh-control/invites', { method: 'POST', body: JSON.stringify({ email }) })
}

export function revokeUsRefreshUser(userId: number): Promise<null> {
  return request(`/us-refresh-control/invites/${userId}`, { method: 'DELETE' })
}

export function getPseValuation(ticker: string): Promise<PseValuation> {
  return request<PseValuation>(`/pse-valuations/${ticker}`)
}

export function getPseValuationCalculator(ticker: string): Promise<PseCalculatorView> {
  return request<PseCalculatorView>(`/pse-valuations/${ticker}/calculator`)
}

export function getPseValuationHistory(ticker: string): Promise<PseValuationHistory> {
  return request<PseValuationHistory>(`/pse-valuations/${ticker}/history`)
}

export function calculatePseValuation(
  ticker: string,
  body: { overrides: Record<string, number>; manual_price?: number; save?: boolean; scenario?: 'low' | 'base' | 'high' },
): Promise<PseCalculatorResult> {
  return request<PseCalculatorResult>(`/pse-valuations/${ticker}/calculator`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// Filing-only U.S. valuations (precomputed, reviewed, price-free public artifact).
export function listUsValuations(): Promise<UsValuationList> {
  return request<UsValuationList>('/us-valuations')
}

export function getUsValuation(ticker: string): Promise<UsValuation> {
  return request<UsValuation>(`/us-valuations/${ticker}`)
}

export function getUsValuationCalculator(ticker: string): Promise<UsCalculatorView> {
  return request<UsCalculatorView>(`/us-valuations/${ticker}/calculator`)
}

export function getUsValuationHistory(ticker: string): Promise<UsValuationHistory> {
  return request<UsValuationHistory>(`/us-valuations/${ticker}/history`)
}

export async function calculateUsValuation(
  ticker: string,
  body: { overrides: Record<string, number>; manual_price?: number; save?: boolean; scenario?: 'low' | 'base' | 'high'; baseline_version?: string; recipe_version?: string | null },
): Promise<UsCalculatorResult> {
  const result = await request<UsCalculatorResult>(`/us-valuations/${ticker}/calculator`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  // Staged/newer APIs return an explicit unavailable comparison for zero
  // values or absent prices; the redesigned UI represents that as null.
  return { ...result, comparison: result.comparison?.status === 'available' ? result.comparison : null }
}
