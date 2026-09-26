import { useEffect, useMemo, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Bell,
  BriefcaseBusiness,
  LogOut,
  Newspaper,
  Scale,
  Search,
  Sparkles,
  X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { listPseValuations, listUsValuations } from '../lib/api'
import type { PseValuationSummary, UsValuationSummary } from '../lib/types'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/valuation/AAPL', label: 'Valuation', icon: Scale, match: '/valuation' },
  { to: '/news', label: 'News', icon: Newspaper, match: '/news' },
  { to: '/portfolio', label: 'Portfolio', icon: BriefcaseBusiness, match: '/portfolio' },
  { to: '/ai-insights', label: 'AI Insights', icon: Sparkles, match: '/ai-insights' },
]

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const isPse = location.pathname.startsWith('/pse')
  const valuationHome = isPse ? '/pse/AP' : '/valuation/AAPL'
  const inputRef = useRef<HTMLInputElement>(null)
  const [usCompanies, setUsCompanies] = useState<UsValuationSummary[]>([])
  const [pseCompanies, setPseCompanies] = useState<PseValuationSummary[]>([])
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)

  useEffect(() => {
    let current = true
    listUsValuations()
      .then(result => { if (current) setUsCompanies(result.items) })
      .catch(() => { if (current) setUsCompanies([]) })
    listPseValuations()
      .then(result => { if (current) setPseCompanies(result.items) })
      .catch(() => { if (current) setPseCompanies([]) })
    return () => { current = false }
  }, [])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        inputRef.current?.focus()
        setSearchOpen(true)
      }
      if (event.key === 'Escape') {
        setSearchOpen(false)
        setAccountOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const results = useMemo(() => {
    const companies = isPse ? pseCompanies : usCompanies
    const needle = query.trim().toLowerCase()
    if (!needle) return companies
    return companies
      .filter((company) =>
        company.ticker.toLowerCase().includes(needle)
        || (company.name ?? '').toLowerCase().includes(needle),
      )
  }, [isPse, pseCompanies, query, usCompanies])

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  function chooseCompany(ticker: string) {
    setQuery('')
    setSearchOpen(false)
    navigate(isPse ? `/pse/${ticker}` : `/valuation/${ticker}`)
  }

  return (
    <div className="finsight-app min-h-screen bg-[var(--app-bg)] text-[var(--app-text)]">
      <header className="sticky top-0 z-50 border-b border-[var(--app-border)] bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex min-h-[76px] max-w-[1480px] flex-wrap items-center gap-4 px-5 py-3 sm:flex-nowrap lg:px-8">
          <NavLink to={valuationHome} className="flex shrink-0 items-center gap-3 no-underline">
            <span className="finsight-brand-mark grid h-10 w-10 place-items-center rounded-xl bg-[#0a0b0d] text-lg font-black text-white shadow-[0_8px_24px_rgba(0,0,0,.14)]">
              F
            </span>
            <span className="text-xl font-bold tracking-[-.04em]">FinSight</span>
          </NavLink>

          <div className="relative order-3 w-full sm:order-none sm:mx-auto sm:max-w-[520px]">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[var(--app-muted)]" />
            <input
              ref={inputRef}
              value={query}
              onFocus={() => setSearchOpen(true)}
              onChange={(event) => {
                setQuery(event.target.value)
                setSearchOpen(true)
              }}
              aria-label="Search company or ticker"
              placeholder="Search company or ticker…"
              className="h-12 w-full rounded-2xl border border-[var(--app-border)] bg-[var(--app-surface)] pl-12 pr-16 text-sm shadow-[0_4px_18px_rgba(15,23,42,.04)] outline-none focus:border-[#a8adb7] focus:ring-4 focus:ring-black/5"
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-[var(--app-border)] bg-white px-2 py-1 text-[10px] font-semibold text-[var(--app-muted)]">
              ⌘K
            </span>

            {searchOpen && (
              <div
                className="absolute left-0 right-0 top-[58px] z-50 flex flex-col overflow-hidden rounded-2xl border border-[var(--app-border)] bg-white p-2 shadow-[0_24px_70px_rgba(15,23,42,.16)]"
                style={{ maxHeight: 'min(70vh, 620px)' }}
              >
                <div className="flex shrink-0 items-center justify-between px-3 py-2 text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">
                  <span>{isPse ? 'Confirmed PH valuations' : 'Confirmed US valuations'}</span>
                  <span>{isPse ? `${pseCompanies.length} · PSE V2` : '100 · Batches 01–10'}</span>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain" aria-label="Company search results">
                  {results.length === 0 ? (
                    <p className="px-3 py-6 text-center text-sm text-[var(--app-muted)]">No company found.</p>
                  ) : (
                    results.map((company) => (
                      <button
                        type="button"
                        key={company.ticker}
                        onClick={() => chooseCompany(company.ticker)}
                        className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-[var(--app-subtle)]"
                      >
                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f1f2f4] text-xs font-black">
                          {company.ticker.slice(0, 2)}
                        </span>
                        <span className="min-w-0 flex-1">
                          <strong className="block truncate text-sm">{company.name ?? company.ticker}</strong>
                          <span className="text-xs text-[var(--app-muted)]">{isPse ? `PH · ${company.ticker}` : `US · ${company.ticker} · Batch ${(company as UsValuationSummary).batch}`}</span>
                        </span>
                        <span className={cn(
                          'rounded-full px-2 py-1 text-[9px] font-bold uppercase tracking-[.08em]',
                          company.availability_type === 'not_available'
                            ? 'bg-[#f1f2f4] text-[var(--app-muted)]'
                            : 'bg-[#eef8f2] text-[#16794b]',
                        )}>
                          {company.availability_type === 'not_available' ? 'Unavailable' : isPse ? humanizeAvailability((company as PseValuationSummary).availability_type) : (company as UsValuationSummary).reliability ?? 'Reviewed'}
                        </span>
                      </button>
                    ))
                  )}
                </div>
                <div className="shrink-0 border-t border-[var(--app-border)] px-3 py-2 text-[10px] text-[var(--app-muted)]">
                  {query.trim() ? `${results.length} matching companies` : 'Scroll to browse · type to filter'}
                </div>
              </div>
            )}
          </div>

          <div className="ml-auto flex shrink-0 items-center gap-2">
            <button
              type="button"
              aria-disabled="true"
              title="Notifications coming soon"
              className="grid h-11 w-11 place-items-center rounded-xl border border-[var(--app-border)] bg-white text-[var(--app-muted)] shadow-sm"
            >
              <Bell className="h-5 w-5" />
            </button>
            <div className="relative">
              <button
                type="button"
                onClick={() => setAccountOpen((open) => !open)}
                aria-label="Open account menu"
                className="grid h-11 w-11 place-items-center rounded-full bg-[#111318] text-sm font-bold text-white shadow-sm"
              >
                {(user?.email?.[0] ?? 'U').toUpperCase()}
              </button>
              {accountOpen && (
                <div className="absolute right-0 top-[52px] w-64 rounded-2xl border border-[var(--app-border)] bg-white p-3 shadow-[0_20px_60px_rgba(15,23,42,.16)]">
                  <div className="flex items-start justify-between gap-3 px-2 py-2">
                    <div className="min-w-0">
                      <p className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">Signed in</p>
                      <p className="mt-1 truncate text-sm font-semibold">{user?.email}</p>
                    </div>
                    <button type="button" onClick={() => setAccountOpen(false)} aria-label="Close account menu">
                      <X className="h-4 w-4 text-[var(--app-muted)]" />
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="mt-2 flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-semibold hover:bg-[var(--app-subtle)]"
                  >
                    <LogOut className="h-4 w-4" /> Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {(searchOpen || accountOpen) && (
        <button
          type="button"
          aria-label="Close open menu"
          className="fixed inset-0 z-40 cursor-default"
          onClick={() => {
            setSearchOpen(false)
            setAccountOpen(false)
          }}
        />
      )}

      <main className="mx-auto min-h-[calc(100vh-76px)] w-full max-w-[1480px] px-5 pb-36 pt-7 lg:px-8 lg:pt-9">
        <div key={location.pathname} className="page-enter">
          <Outlet />
        </div>
      </main>

      <nav
        className="finsight-dock fixed bottom-4 left-1/2 z-50 grid w-[calc(100%-24px)] max-w-[660px] -translate-x-1/2 grid-cols-4 rounded-[24px] border border-[var(--app-border)] bg-white/95 p-1.5 shadow-[0_18px_55px_rgba(15,23,42,.16)] backdrop-blur-xl sm:bottom-6"
        aria-label="Primary navigation"
      >
        {NAV.map(({ to, label, icon: Icon, match }) => {
          const destination = label === 'Valuation' ? valuationHome : to
          const active = label === 'Valuation' ? (location.pathname.startsWith('/valuation') || isPse) : location.pathname.startsWith(match)
          return (
            <NavLink
              key={label}
              to={destination}
              data-active={active}
              className={cn(
                'relative flex min-h-14 flex-col items-center justify-center gap-1 rounded-[18px] px-2 text-[10px] font-semibold text-[var(--app-muted)] sm:min-h-12 sm:flex-row sm:gap-2 sm:text-xs',
                active && 'bg-[#101216] text-white shadow-[0_8px_22px_rgba(15,23,42,.18)]',
              )}
            >
              <Icon className="h-[18px] w-[18px]" />
              <span>{label}</span>
              {active && <span className="absolute -bottom-1 h-1 w-1 rounded-full bg-current sm:hidden" />}
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}

function humanizeAvailability(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase())
}
