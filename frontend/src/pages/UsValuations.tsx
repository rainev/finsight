import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ExternalLink, RotateCcw, Save, SlidersHorizontal } from 'lucide-react'
import { calculateUsValuation, getUsValuation, getUsValuationCalculator, listUsValuations } from '@/lib/api'
import type { UsAvailabilityType, UsCalculatorResult, UsCalculatorView, UsModelResult, UsValuation, UsValuationSummary } from '@/lib/types'
import { PageHeading, panel, percent } from '@/lib/format'
import { cn } from '@/lib/utils'

const usd = (value: number | null | undefined, digits = 2) => Number.isFinite(value)
  ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value as number)
  : '—'
const humanize = (value: string | undefined) => (value ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
const availabilityLabel: Record<UsAvailabilityType, string> = { available: 'Available', conditional_estimate: 'Conditional estimate', relative_baseline: 'Relative baseline', not_available: 'Not available' }

function StateBadge({ state }: { state: UsAvailabilityType }) {
  const tone = state === 'available' ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500' : state === 'not_available' ? 'border-red-500/40 bg-red-500/10 text-red-500' : 'border-amber-500/40 bg-amber-500/10 text-amber-500'
  return <span className={cn('rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[.12em]', tone)}>{availabilityLabel[state]}</span>
}

function ModelCard({ label, primary, result }: { label: string; primary?: boolean; result: UsModelResult | undefined }) {
  if (!result) return null
  const value = result.conditional_value_per_share ?? result.intrinsic_value_per_share
  return <div className={cn(panel, 'p-5')}>
    <p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">{label}{primary && <span className="ml-2 text-[var(--app-text)]">· primary</span>}</p>
    <p className="mt-3 font-serif text-3xl font-semibold tracking-[-.03em]">{usd(value)}</p>
    <p className="mt-1 text-xs text-[var(--app-muted)]">{result.model === 'conditional_estimate' ? 'conditional value / share' : 'intrinsic value / share'}</p>
    {result.warnings?.length > 0 && <ul className="mt-3 space-y-1">{result.warnings.map((warning, index) => <li key={index} className="flex gap-1.5 text-[11px] leading-snug text-amber-500"><AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" /> {warning}</li>)}</ul>}
  </div>
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--app-muted)]">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div>
}

export default function UsValuations() {
  const [list, setList] = useState<UsValuationSummary[]>([])
  const [ticker, setTicker] = useState('AAPL')
  const [data, setData] = useState<UsValuation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scenario, setScenario] = useState<'low' | 'base' | 'high'>('base')
  const [calculator, setCalculator] = useState<UsCalculatorView | null>(null)
  const [calculatorOpen, setCalculatorOpen] = useState(false)
  const [calculatorValues, setCalculatorValues] = useState<Record<string, string>>({})
  const [manualPrice, setManualPrice] = useState('')
  const [calculated, setCalculated] = useState<UsCalculatorResult | null>(null)
  const [calculatorError, setCalculatorError] = useState<string | null>(null)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)

  useEffect(() => { listUsValuations().then((response) => { setList(response.items); if (response.items.length && !response.items.some((item) => item.ticker === 'AAPL')) setTicker(response.items[0].ticker) }).catch(() => {}) }, [])
  useEffect(() => {
    let live = true
    setLoading(true); setError(null); setCalculated(null); setCalculator(null); setCalculatorOpen(false); setManualPrice(''); setScenario('base')
    Promise.all([getUsValuation(ticker), getUsValuationCalculator(ticker)])
      .then(([detail, view]) => { if (!live) return; setData(detail); setCalculator(view); setCalculatorValues(Object.fromEntries(Object.entries(view.defaults).map(([key, value]) => [key, String(value)]))) })
      .catch((caught: Error) => live && setError(caught.message)).finally(() => live && setLoading(false))
    return () => { live = false }
  }, [ticker])

  const overrides = useMemo(() => Object.fromEntries(Object.entries(calculatorValues).map(([key, value]) => [key, Number(value)]).filter(([, value]) => Number.isFinite(value))), [calculatorValues])
  useEffect(() => {
    if (!calculatorOpen || !calculator?.can_calculate) return
    const timer = window.setTimeout(() => {
      calculateUsValuation(ticker, { overrides, ...(manualPrice && Number(manualPrice) > 0 ? { manual_price: Number(manualPrice) } : {}) })
        .then((result) => { setCalculated(result); setCalculatorError(null) }).catch((caught: Error) => setCalculatorError(caught.message))
    }, 250)
    return () => window.clearTimeout(timer)
  }, [calculatorOpen, calculator, ticker, overrides, manualPrice])

  const range = calculated?.result ?? data?.scenario_range
  const selectedValue = range?.[scenario]
  const pa = data?.public_assumptions
  const segments = pa?.segment_assumptions ? Object.values(pa.segment_assumptions) : []
  const comparison = calculated?.comparison ?? data?.market_comparison

  function resetCalculator() {
    if (!calculator) return
    setCalculatorValues(Object.fromEntries(Object.entries(calculator.defaults).map(([key, value]) => [key, String(value)])))
    setManualPrice(''); setCalculated(null); setSavedMessage(null)
  }
  async function saveCalculator() {
    const result = await calculateUsValuation(ticker, { overrides, ...(manualPrice && Number(manualPrice) > 0 ? { manual_price: Number(manualPrice) } : {}), save: true })
    setCalculated(result); setSavedMessage(`Saved custom valuation #${result.saved_id}`)
  }

  return <div>
    <PageHeading eyebrow="U.S. filings · FinSight baseline" title="US Valuations" description="Bear, base, and bull decision-support values with confidence, assumptions, and warnings. Educational estimates—not recommendations." />
    <div className="mb-7 flex flex-wrap items-center gap-3"><select value={ticker} onChange={(event) => setTicker(event.target.value)} className="rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] px-3 py-2 text-sm font-semibold text-[var(--app-text)]">{list.map((item) => <option key={item.ticker} value={item.ticker}>{item.ticker}{item.name ? ` — ${item.name}` : ''}</option>)}</select>{list.length > 0 && <span className="text-xs text-[var(--app-muted)]">{list.length} company baselines</span>}</div>
    {loading && <p className="text-sm text-[var(--app-muted)]">Loading {ticker}…</p>}
    {error && !loading && <div className={cn(panel, 'flex items-center gap-2 p-5 text-sm text-red-500')}><AlertTriangle className="h-4 w-4" /> Could not load {ticker}: {error}</div>}
    {data && !loading && !error && <div className="space-y-6">
      <div className={cn(panel, 'p-6')}><div className="flex flex-wrap items-start justify-between gap-5"><div><div className="flex items-center gap-3"><h2 className="text-2xl font-semibold tracking-[-.02em]">{data.issuer.issuer_name}</h2><StateBadge state={data.availability_type} /></div><p className="mt-1 text-sm text-[var(--app-muted)]">{data.ticker} · {data.issuer.finsight_sector} · {humanize(data.primary_valuation_method)}</p></div><div className="text-right"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--app-muted)]">FinSight {scenario} case</p><p className="font-serif text-4xl font-semibold tracking-[-.03em]">{usd(selectedValue)}</p><div className="mt-3 flex rounded-lg border border-[var(--app-border)] p-1">{(['low', 'base', 'high'] as const).map((key) => <button key={key} onClick={() => setScenario(key)} className={cn('rounded-md px-3 py-1 text-xs font-semibold', scenario === key && 'bg-[var(--app-text)] text-[var(--app-bg)]')}>{key === 'low' ? 'Bear' : key === 'high' ? 'Bull' : 'Base'}</button>)}</div></div></div></div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className={cn(panel, 'p-5')}><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--app-muted)]">Confidence</p><p className="mt-2 text-2xl font-semibold">{data.confidence.label ?? 'Unavailable'}</p><p className="mt-2 text-xs leading-relaxed text-[var(--app-muted)]">{data.confidence.reasons.length ? data.confidence.reasons.map(humanize).join(' · ') : 'Reported inputs and scenario width drive this label.'}</p></div>
        <div className={cn(panel, 'p-5')}><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--app-muted)]">Market comparison</p><p className="mt-2 text-lg font-semibold">{comparison?.status === 'available' ? comparison.label : 'Comparison unavailable'}</p><p className="mt-2 text-xs text-[var(--app-muted)]">{comparison?.price_date ? `EOD date ${comparison.price_date}; raw price stays private.` : manualPrice ? 'Using your price.' : 'No approved EOD record is attached.'}</p></div>
        <div className={cn(panel, 'p-5')}><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--app-muted)]">Relative cross-check</p><p className="mt-2 text-lg font-semibold">{data.relative_value_summary.status === 'available' ? usd(data.relative_value_summary.base) : 'Not available'}</p><p className="mt-2 text-xs text-[var(--app-muted)]">{data.relative_value_summary.label ?? 'No approved comparable cohort and private peer record.'}</p></div>
      </div>
      <div className={cn(panel, 'p-6')}><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">Your assumptions</p><p className="mt-1 text-sm text-[var(--app-muted)]">Source facts, identity, shares, and history stay locked.</p></div><button disabled={!calculator?.can_calculate} onClick={() => setCalculatorOpen((open) => !open)} className="inline-flex items-center gap-2 rounded-lg bg-[var(--app-text)] px-4 py-2 text-xs font-semibold text-[var(--app-bg)] disabled:opacity-40"><SlidersHorizontal className="h-4 w-4" /> Edit assumptions</button></div>
        {calculatorOpen && calculator?.can_calculate && <div className="mt-5 border-t border-[var(--app-border)] pt-5"><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{calculator.editable_assumptions.map((field) => <label key={field.key} className="grid gap-1 text-xs font-semibold"><span>{field.label}</span><input type="number" min={field.min} max={field.max} step={field.step} value={calculatorValues[field.key] ?? ''} onChange={(event) => setCalculatorValues((values) => ({ ...values, [field.key]: event.target.value }))} className="h-10 rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] px-3" /></label>)}<label className="grid gap-1 text-xs font-semibold"><span>Your price (optional)</span><input type="number" min="0.01" step="0.01" value={manualPrice} onChange={(event) => setManualPrice(event.target.value)} placeholder="Automatic EOD when blank" className="h-10 rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] px-3" /></label></div>{calculatorError && <p className="mt-3 text-xs text-red-500">{calculatorError}</p>}{calculated && <p className="mt-4 text-sm">Your base case: <strong>{usd(calculated.result.base)}</strong> · {calculated.comparison_source === 'manual' ? 'Using your price' : 'Using automatic EOD comparison'}</p>}<div className="mt-4 flex flex-wrap gap-2"><button onClick={resetCalculator} className="inline-flex items-center gap-2 rounded-lg border border-[var(--app-border)] px-3 py-2 text-xs font-semibold"><RotateCcw className="h-4 w-4" /> Reset to FinSight assumptions</button><button onClick={saveCalculator} className="inline-flex items-center gap-2 rounded-lg border border-[var(--app-border)] px-3 py-2 text-xs font-semibold"><Save className="h-4 w-4" /> Save custom valuation</button></div>{savedMessage && <p className="mt-2 text-xs text-emerald-500">{savedMessage}</p>}</div>}
      </div>
      <div className="grid gap-4 md:grid-cols-2">{Object.entries(data.models ?? {}).map(([key, result]) => <ModelCard key={key} label={humanize(key)} primary={key === data.model_policy?.primary} result={result} />)}</div>
      {pa && <div className={cn(panel, 'p-6')}><p className="mb-4 text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">Main assumptions</p><div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-6">{Object.entries(pa).filter(([, value]) => typeof value === 'number' || typeof value === 'string' || typeof value === 'boolean').map(([key, value]) => <Stat key={key} label={humanize(key)} value={typeof value === 'number' ? Math.abs(value) < 1 ? percent(value) : String(Math.round(value * 100) / 100) : humanize(String(value))} />)}</div>{segments.length > 0 && <div className="mt-6 border-t border-[var(--app-border)] pt-5"><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{segments.map((segment) => <div key={segment.label} className="rounded-xl border border-[var(--app-border)] p-3.5"><p className="text-sm font-semibold">{segment.label}</p><p className="mt-1 text-xs text-[var(--app-muted)]">growth {percent(segment.initial_revenue_growth ?? null)} · margin {percent(segment.target_gross_margin ?? segment.target_operating_margin ?? null)}</p></div>)}</div></div>}</div>}
      <div className={cn(panel, 'p-6')}><p className="mb-3 text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">Source filing</p><div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm"><span className="font-semibold">{data.source_financial_statement.form}</span><span className="text-[var(--app-muted)]">period end {data.source_financial_statement.period_end}</span><span className="text-[var(--app-muted)]">filed {data.source_financial_statement.filed_date}</span><a href={data.source_financial_statement.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold underline decoration-dotted">SEC filing <ExternalLink className="h-3.5 w-3.5" /></a></div><p className="mt-4 text-[11px] leading-relaxed text-[var(--app-muted)]">Derived values, assumptions, warnings, and filing attribution only—no raw vendor prices or recommendations. Valuation date {data.valuation_date}.</p></div>
    </div>}
  </div>
}
