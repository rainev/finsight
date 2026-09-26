import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, Bookmark, BriefcaseBusiness, Plus, Trash2 } from 'lucide-react'
import {
  addHolding,
  deleteValuation,
  listHoldings,
  listPseValuations,
  listUsValuations,
  listValuations,
  removeHolding,
} from '../lib/api'
import type { Holding, PseValuationSummary, SavedValuation, UsValuationSummary } from '../lib/types'
import { cn } from '@/lib/utils'

const money = (value: number | null | undefined, currency = 'USD') =>
  Number.isFinite(value)
    ? new Intl.NumberFormat(currency === 'PHP' ? 'en-PH' : 'en-US', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2,
      }).format(value as number)
    : '—'

export default function Portfolio() {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') === 'saved' ? 'saved' : 'companies'
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [companies, setCompanies] = useState<UsValuationSummary[]>([])
  const [pseCompanies, setPseCompanies] = useState<PseValuationSummary[]>([])
  const [saved, setSaved] = useState<SavedValuation[]>([])
  const [ticker, setTicker] = useState('AAPL')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([listHoldings(), listUsValuations(), listPseValuations(), listValuations()])
      .then(([holdingRows, catalog, pseCatalog, savedRows]) => {
        setHoldings(holdingRows)
        setCompanies(catalog.items)
        setPseCompanies(pseCatalog.items)
        setSaved(savedRows)
        const firstUnheld = catalog.items.find((company) => !holdingRows.some((holding) => holding.market === 'US' && holding.ticker === company.ticker))
        if (firstUnheld) setTicker(firstUnheld.ticker)
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Failed to load portfolio'))
      .finally(() => setLoading(false))
  }, [])

  const catalogByTicker = useMemo(() => new Map(companies.map((company) => [company.ticker, company])), [companies])
  const pseCatalogByTicker = useMemo(() => new Map(pseCompanies.map((company) => [company.ticker, company])), [pseCompanies])
  const availableToAdd = companies.filter((company) => !holdings.some((holding) => holding.market === 'US' && holding.ticker === company.ticker))

  async function add(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const row = await addHolding(ticker, 'US')
      setHoldings((current) => [...current.filter((holding) => holding.id !== row.id), row])
      const next = companies.find((company) => company.ticker !== ticker && !holdings.some((holding) => holding.ticker === company.ticker))
      if (next) setTicker(next.ticker)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not add company')
    } finally {
      setSaving(false)
    }
  }

  async function removeCompany(row: Holding) {
    if (!window.confirm(`Remove ${row.ticker} from your portfolio?`)) return
    await removeHolding(row.id)
    setHoldings((current) => current.filter((holding) => holding.id !== row.id))
  }

  async function removeSaved(id: number) {
    if (!window.confirm('Delete this saved valuation scenario?')) return
    await deleteValuation(id)
    setSaved((current) => current.filter((row) => row.id !== id))
  }

  return (
    <section>
      <header className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[var(--app-muted)]">Your portfolio</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-.05em] sm:text-5xl">Companies worth watching.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--app-muted)]">A simple watchlist for confirmed US and PH valuation catalogs—without fabricated performance or live-price data.</p>
        </div>
        <div className="inline-grid grid-cols-2 rounded-2xl border border-[var(--app-border)] bg-white p-1 shadow-sm">
          <button type="button" onClick={() => setParams({})} className={cn('rounded-xl px-4 py-2.5 text-xs font-semibold', tab === 'companies' ? 'bg-[#111318] text-white' : 'text-[var(--app-muted)]')}>Companies</button>
          <button type="button" onClick={() => setParams({ tab: 'saved' })} className={cn('rounded-xl px-4 py-2.5 text-xs font-semibold', tab === 'saved' ? 'bg-[#111318] text-white' : 'text-[var(--app-muted)]')}>Saved scenarios</button>
        </div>
      </header>

      {error && <p className="mt-5 rounded-2xl border border-[#f2c9cf] bg-[#fff7f8] px-4 py-3 text-sm text-[#a02f43]">{error}</p>}

      {tab === 'companies' ? (
        <>
          <form onSubmit={add} className="mt-8 flex flex-col gap-3 rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_14px_38px_rgba(15,23,42,.04)] sm:flex-row sm:items-end sm:p-6">
            <label className="grid flex-1 gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">Add a confirmed US company</span>
              <select value={ticker} onChange={(event) => setTicker(event.target.value)} disabled={availableToAdd.length === 0} className="h-12 rounded-xl border border-[var(--app-border)] bg-[#fbfbfc] px-3 text-sm outline-none focus:border-[#9ca3af]">
                {availableToAdd.map((company) => <option key={company.ticker} value={company.ticker}>{company.ticker} — {company.name}</option>)}
              </select>
            </label>
            <button type="submit" disabled={saving || availableToAdd.length === 0} className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-[#111318] px-5 text-sm font-semibold text-white shadow-sm hover:-translate-y-0.5 disabled:opacity-50">
              <Plus className="h-4 w-4" /> {saving ? 'Adding…' : 'Add company'}
            </button>
          </form>

          {loading ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="h-52 animate-pulse rounded-[24px] bg-white" />)}</div>
          ) : holdings.length === 0 ? (
            <div className="mt-6 rounded-[26px] border border-dashed border-[var(--app-border)] bg-white px-6 py-16 text-center">
              <BriefcaseBusiness className="mx-auto h-8 w-8 text-[var(--app-muted)]" />
              <h2 className="mt-4 text-xl font-semibold">Your portfolio is empty.</h2>
              <p className="mt-2 text-sm text-[var(--app-muted)]">Add a company above or from its valuation page.</p>
            </div>
          ) : (
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {holdings.map((holding) => {
                const catalog = holding.market === 'US' ? catalogByTicker.get(holding.ticker) : pseCatalogByTicker.get(holding.ticker)
                return (
                  <article key={holding.id} className="group rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,.04)] transition hover:-translate-y-1 hover:shadow-[0_18px_44px_rgba(15,23,42,.08)]">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#f1f2f4] text-xs font-black">{holding.ticker.slice(0, 2)}</span>
                        <div className="min-w-0">
                          <strong className="block truncate text-base">{holding.name}</strong>
                          <span className="mt-1 block text-xs text-[var(--app-muted)]">{holding.market} · {holding.ticker}</span>
                        </div>
                      </div>
                      <button type="button" onClick={() => removeCompany(holding)} aria-label={`Remove ${holding.ticker}`} className="grid h-9 w-9 place-items-center rounded-xl text-[var(--app-muted)] opacity-70 hover:bg-[#fff0f2] hover:text-[#d12e4f] group-hover:opacity-100">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="mt-7 grid grid-cols-2 gap-3">
                      <div><p className="text-[9px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">Base value</p><strong className="mt-1 block text-xl tabular-nums">{money(catalog?.base, holding.currency)}</strong></div>
                      <div><p className="text-[9px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">Status</p><strong className="mt-1 block text-sm">{catalog?.availability_type === 'not_available' ? 'Unavailable' : holding.market === 'US' ? (catalog as UsValuationSummary | undefined)?.reliability ?? 'Tracked' : (catalog as PseValuationSummary | undefined)?.availability_type.replace(/_/g, ' ') ?? 'Tracked'}</strong></div>
                    </div>
                    <Link to={holding.market === 'US' ? `/valuation/${holding.ticker}` : `/pse/${holding.ticker}`} className="mt-6 flex items-center justify-between border-t border-[var(--app-border)] pt-4 text-xs font-semibold">
                      Open valuation <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </Link>
                  </article>
                )
              })}
            </div>
          )}
        </>
      ) : (
        <div className="mt-8">
          {loading ? (
            <div className="h-52 animate-pulse rounded-[24px] bg-white" />
          ) : saved.length === 0 ? (
            <div className="rounded-[26px] border border-dashed border-[var(--app-border)] bg-white px-6 py-16 text-center">
              <Bookmark className="mx-auto h-8 w-8 text-[var(--app-muted)]" />
              <h2 className="mt-4 text-xl font-semibold">No saved scenarios yet.</h2>
              <p className="mt-2 text-sm text-[var(--app-muted)]">Adjust assumptions on a company and choose Save scenario.</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {saved.map((row) => {
                const isUs = Boolean(row.us_company)
                const selectedCase = row.result.selected_scenario === 'low' || row.result.selected_scenario === 'high' ? row.result.selected_scenario : 'base'
                const base = row.result[selectedCase] ?? row.result.base ?? row.result.intrinsic_value
                return (
                  <article key={row.id} className="rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,.04)]">
                    <div className="flex items-start justify-between gap-3">
                      <div><p className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">{isUs ? row.ticker : `PSE · ${row.ticker ?? 'valuation'}`}</p><h2 className="mt-1 text-base font-semibold">{row.model.replace(/_/g, ' ')}</h2></div>
                      <button type="button" onClick={() => removeSaved(row.id)} aria-label="Delete saved valuation" className="grid h-9 w-9 place-items-center rounded-xl text-[var(--app-muted)] hover:bg-[#fff0f2] hover:text-[#d12e4f]"><Trash2 className="h-4 w-4" /></button>
                    </div>
                    <strong className="mt-7 block text-3xl tracking-[-.04em] tabular-nums">{money(base, isUs ? 'USD' : 'PHP')}</strong>
                    {isUs && <p className="mt-2 text-xs text-[var(--app-muted)]">{selectedCase === 'low' ? 'Bear case' : selectedCase === 'high' ? 'Bull case' : 'Base case'}</p>}
                    <p className="mt-2 text-xs text-[var(--app-muted)]">{new Date(row.created_at).toLocaleString()}</p>
                    {row.result.comparison?.label && <p className="mt-4 rounded-xl bg-[#f5f6f7] px-3 py-2 text-xs">{row.result.comparison.label}</p>}
                    {row.ticker && <Link to={isUs ? `/valuation/${row.ticker}` : `/pse/${row.ticker}`} className="mt-5 inline-flex items-center gap-2 text-xs font-semibold">Open company <ArrowRight className="h-3.5 w-3.5" /></Link>}
                  </article>
                )
              })}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
