import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ExternalLink, RotateCcw, Save, SlidersHorizontal } from 'lucide-react'
import { calculateUsValuation, getUsValuation, getUsValuationCalculator, listUsValuations } from '@/lib/api'
import type { UsCalculatorResult, UsCalculatorView, UsModelResult, UsValuation, UsValuationSummary } from '@/lib/types'
import { PageHeading, panel, percent } from '@/lib/format'
import { cn } from '@/lib/utils'

const usd = (value: number | null | undefined, digits = 2) => Number.isFinite(value)
  ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value as number)
  : '—'
const humanize = (value: string | undefined) => (value ?? '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
const percentAssumptionKeys = new Set([
  'initial_revenue_growth',
  'target_operating_margin',
  'target_gross_margin',
  'terminal_growth',
  'policy_wacc',
  'risk_free_rate',
  'equity_risk_premium',
  'cash_conversion_margin',
  'cash_conversion_margin_low',
  'cash_conversion_margin_high',
])
const percentCalculatorKeys = new Set([
  'sustainable_roe',
  'payout_ratio',
  'discount_rate',
  'terminal_growth',
  'affo_growth',
  'recurring_cost_ratio',
  'dividend_growth',
  'initial_growth',
])
const calculatorDisplayValue = (key: string, value: number) => percentCalculatorKeys.has(key)
  ? (value * 100).toFixed(2)
  : String(value)
const calculatorModelValue = (key: string, value: string) => {
  const parsed = Number(value)
  return percentCalculatorKeys.has(key) ? parsed / 100 : parsed
}
const calculatorDisplayBoundary = (key: string, value: number) => percentCalculatorKeys.has(key)
  ? value * 100
  : value
const formatAssumption = (key: string, value: string | number | boolean) => {
  if (typeof value === 'number') {
    return percentAssumptionKeys.has(key) ? percent(value) : String(Math.round(value * 100) / 100)
  }
  return humanize(String(value))
}
const cleanExplanation = (value: string | undefined) => (value ?? '')
  .replace(/^CANDIDATE\s*\(review_required\)\s*[—-]\s*/i, '')
  .replace(/^Conditional Low(?: current-state)? estimate\.\s*/i, '')
  .replace(/^Conditional estimate\.\s*/i, '')
  .replace(/^Withheld\.\s*/i, '')
  .replace(/\bConditional Low\b/gi, 'baseline')
  .replace(/\bConditional estimate\b/gi, 'baseline estimate')
  .replace(/;?\s*reliability capped at Low\.?/gi, '.')
  .replace(/[^.]*\bis capped at Low\.?/gi, '')
  .trim()
const methodLabel = (data: UsValuation) => {
  const method = data.availability_type === 'conditional_estimate'
    ? data.model_policy.fallback_from ?? 'intrinsic_valuation'
    : data.primary_valuation_method
  const labels: Record<string, string> = {
    fcff_dcf: 'Cash flow valuation',
    ddm: 'Dividend valuation',
    residual_income: 'Residual income valuation',
    ffo: 'Funds-from-operations valuation',
    intrinsic_valuation: 'Intrinsic valuation',
  }
  return labels[method] ?? humanize(method)
}

function ModelCard({ label, primary, result, valueOverride }: { label: string; primary?: boolean; result: UsModelResult | undefined; valueOverride?: number }) {
  if (!result) return null
  const value = valueOverride ?? result.conditional_value_per_share ?? result.intrinsic_value_per_share
  return <div className={cn(panel, 'p-5')}>
    <p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">{label}{primary && <span className="ml-2 text-[var(--app-text)]">· primary</span>}</p>
    <p className="mt-3 font-serif text-3xl font-semibold tracking-[-.03em]">{usd(value)}</p>
    <p className="mt-1 text-xs text-[var(--app-muted)]">intrinsic value / share</p>
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
  const [assumptionsDirty, setAssumptionsDirty] = useState(false)

  useEffect(() => { listUsValuations().then((response) => { setList(response.items); if (response.items.length && !response.items.some((item) => item.ticker === 'AAPL')) setTicker(response.items[0].ticker) }).catch(() => {}) }, [])
  useEffect(() => {
    let live = true
    setLoading(true); setError(null); setCalculated(null); setCalculator(null); setCalculatorOpen(false); setManualPrice(''); setScenario('base'); setAssumptionsDirty(false)
    Promise.all([getUsValuation(ticker), getUsValuationCalculator(ticker)])
      .then(([detail, view]) => { if (!live) return; setData(detail); setCalculator(view); setCalculatorValues(Object.fromEntries(Object.entries(view.defaults).map(([key, value]) => [key, calculatorDisplayValue(key, Number(value))]))) })
      .catch((caught: Error) => live && setError(caught.message)).finally(() => live && setLoading(false))
    return () => { live = false }
  }, [ticker])

  const overrides = useMemo(() => Object.fromEntries(Object.entries(calculatorValues).map(([key, value]) => [key, calculatorModelValue(key, value)]).filter(([, value]) => Number.isFinite(value))), [calculatorValues])
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
  const unavailable = data?.availability_type === 'not_available'
  const supportingExplanations = data
    ? [data.model_policy.reason, ...(data.review?.warnings ?? [])]
      .map(cleanExplanation)
      .filter((value, index, values) => value && !value.toLowerCase().startsWith('calculator is calibrated') && values.indexOf(value) === index)
    : []
  const unavailableReason = cleanExplanation(
    data?.review?.errors?.[0]
      ?? data?.review?.warnings?.[0]
      ?? data?.model_policy.reason,
  ) || 'FinSight cannot produce a reliable valuation from the available evidence.'

  function resetCalculator() {
    if (!calculator) return
    setCalculatorValues(Object.fromEntries(Object.entries(calculator.defaults).map(([key, value]) => [key, calculatorDisplayValue(key, Number(value))])))
    setManualPrice(''); setCalculated(null); setSavedMessage(null); setCalculatorError(null); setAssumptionsDirty(false)
  }
  async function saveCalculator() {
    try {
      const result = await calculateUsValuation(ticker, { overrides, ...(manualPrice && Number(manualPrice) > 0 ? { manual_price: Number(manualPrice) } : {}), save: true })
      setCalculated(result); setSavedMessage(`Saved custom valuation #${result.saved_id}`); setCalculatorError(null)
    } catch (caught) {
      setCalculatorError(caught instanceof Error ? caught.message : 'Could not save this valuation')
      setSavedMessage(null)
    }
  }

  return <div>
    <PageHeading eyebrow="U.S. filings · FinSight baseline" title="Valuations" description="Bear, base, and bull decision-support values with transparent assumptions and warnings. Educational estimates—not recommendations." />
    <div className="mb-7 flex flex-wrap items-center gap-3"><select value={ticker} onChange={(event) => setTicker(event.target.value)} className="rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] px-3 py-2 text-sm font-semibold text-[var(--app-text)]">{list.map((item) => <option key={item.ticker} value={item.ticker}>{item.ticker}{item.name ? ` — ${item.name}` : ''}</option>)}</select>{list.length > 0 && <span className="text-xs text-[var(--app-muted)]">{list.length} company baselines</span>}</div>
    {loading && <p className="text-sm text-[var(--app-muted)]">Loading {ticker}…</p>}
    {error && !loading && <div className={cn(panel, 'flex items-center gap-2 p-5 text-sm text-red-500')}><AlertTriangle className="h-4 w-4" /> Could not load {ticker}: {error}</div>}
    {data && !loading && !error && <div className="space-y-6">
      <div className={cn(panel, 'p-6')}><div className="flex flex-wrap items-start justify-between gap-5"><div><div className="flex items-center gap-3"><h2 className="text-2xl font-semibold tracking-[-.02em]">{data.issuer.issuer_name}</h2>{unavailable && <span className="rounded-full border border-[var(--app-border)] bg-[var(--app-bg)] px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">Valuation unavailable</span>}</div><p className="mt-1 text-sm text-[var(--app-muted)]">{data.ticker} · {data.issuer.finsight_sector} · {unavailable ? 'No reliable valuation' : methodLabel(data)}</p></div><div className="text-right"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--app-muted)]">{unavailable ? 'Intrinsic value per share' : `${assumptionsDirty ? 'Your' : 'FinSight'} ${scenario} case`}</p><p className="font-serif text-4xl font-semibold tracking-[-.03em]">{unavailable ? '—' : usd(selectedValue)}</p>{!unavailable && <div className="mt-3 flex rounded-lg border border-[var(--app-border)] p-1">{(['low', 'base', 'high'] as const).map((key) => <button key={key} onClick={() => setScenario(key)} className={cn('rounded-md px-3 py-1 text-xs font-semibold', scenario === key && 'bg-[var(--app-text)] text-[var(--app-bg)]')}>{key === 'low' ? 'Bear' : key === 'high' ? 'Bull' : 'Base'}</button>)}</div>}</div></div></div>
      {!unavailable && <div className={cn(panel, 'p-5')}><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[var(--app-muted)]">Market comparison</p><p className="mt-2 text-lg font-semibold">{comparison?.status === 'available' ? comparison.label : 'Add a market price to compare'}</p><p className="mt-2 text-xs text-[var(--app-muted)]">{comparison?.price_date ? `EOD date ${comparison.price_date}; raw price stays private.` : comparison?.status === 'available' && manualPrice ? 'Compared with the market price you entered.' : 'Open Your assumptions and enter a market price. It will not change intrinsic value.'}</p></div>}
      {!unavailable && <div className={cn(panel, 'p-6')}><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">Your assumptions</p><p className="mt-1 text-sm text-[var(--app-muted)]">Source facts, identity, shares, and history stay locked.</p></div><button disabled={!calculator?.can_calculate} onClick={() => setCalculatorOpen((open) => !open)} className="inline-flex items-center gap-2 rounded-lg bg-[var(--app-text)] px-4 py-2 text-xs font-semibold text-[var(--app-bg)] disabled:opacity-40"><SlidersHorizontal className="h-4 w-4" /> Edit assumptions</button></div>
        {calculatorOpen && calculator?.can_calculate && <div className="mt-5 border-t border-[var(--app-border)] pt-5"><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{calculator.editable_assumptions.map((field) => <label key={field.key} className="grid gap-1 text-xs font-semibold"><span>{field.label}{percentCalculatorKeys.has(field.key) ? ' (%)' : ''}</span><input type="number" min={calculatorDisplayBoundary(field.key, field.min)} max={calculatorDisplayBoundary(field.key, field.max)} step={calculatorDisplayBoundary(field.key, field.step)} value={calculatorValues[field.key] ?? ''} onChange={(event) => { setCalculatorValues((values) => ({ ...values, [field.key]: event.target.value })); setSavedMessage(null); setAssumptionsDirty(true) }} className="h-10 rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] px-3" /></label>)}<label className="grid gap-1 text-xs font-semibold"><span>Market price (optional)</span><input type="number" min="0.01" step="0.01" value={manualPrice} onChange={(event) => { setManualPrice(event.target.value); setSavedMessage(null) }} placeholder="Used only for comparison" className="h-10 rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] px-3" /><small className="font-normal text-[var(--app-muted)]">Compares price with your value; it does not affect intrinsic value.</small></label></div>{calculatorError && <p className="mt-3 text-xs text-red-500">{calculatorError}</p>}{calculated && <p className="mt-4 text-sm">{assumptionsDirty ? 'Your calculated range' : 'FinSight range'}: <strong>{usd(calculated.result.low)}–{usd(calculated.result.high)}</strong> · Base <strong>{usd(calculated.result.base)}</strong></p>}<div className="mt-4 flex flex-wrap gap-2"><button onClick={resetCalculator} className="inline-flex items-center gap-2 rounded-lg border border-[var(--app-border)] px-3 py-2 text-xs font-semibold"><RotateCcw className="h-4 w-4" /> Reset to FinSight assumptions</button><button onClick={saveCalculator} className="inline-flex items-center gap-2 rounded-lg border border-[var(--app-border)] px-3 py-2 text-xs font-semibold"><Save className="h-4 w-4" /> Save custom valuation</button></div><p className="mt-2 text-[11px] text-[var(--app-muted)]">Save stores your edited assumptions and calculated range in Saved.</p>{savedMessage && <p className="mt-2 text-xs text-emerald-500">{savedMessage}</p>}</div>}
      </div>}
      {!unavailable && <div className="grid gap-4 md:grid-cols-2">{Object.entries(data.models ?? {}).map(([key, result]) => <ModelCard key={key} label={key === 'conditional_estimate' ? 'Intrinsic value' : humanize(key)} primary={key === data.model_policy?.primary} result={result} valueOverride={key === data.model_policy?.primary && assumptionsDirty ? calculated?.result.base : undefined} />)}</div>}
      {unavailable
        ? <div className={cn(panel, 'p-6')}><p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">Why valuation is unavailable</p><p className="mt-3 max-w-3xl text-sm leading-relaxed text-[var(--app-muted)]">{unavailableReason}</p></div>
        : pa && <div className={cn(panel, 'p-6')}><p className="text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">Key assumptions</p>{supportingExplanations.length > 0 && <div className="mt-3 space-y-2">{supportingExplanations.map((explanation) => <p key={explanation} className="max-w-4xl text-sm leading-relaxed text-[var(--app-muted)]">{explanation}</p>)}</div>}<div className="mt-5 grid grid-cols-2 gap-5 border-t border-[var(--app-border)] pt-5 sm:grid-cols-3 lg:grid-cols-6">{Object.entries(pa).filter(([, value]) => typeof value === 'number' || typeof value === 'string' || typeof value === 'boolean').map(([key, value]) => <Stat key={key} label={humanize(key)} value={formatAssumption(key, value as string | number | boolean)} />)}</div>{segments.length > 0 && <div className="mt-6 border-t border-[var(--app-border)] pt-5"><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{segments.map((segment) => <div key={segment.label} className="rounded-xl border border-[var(--app-border)] p-3.5"><p className="text-sm font-semibold">{segment.label}</p><p className="mt-1 text-xs text-[var(--app-muted)]">growth {percent(segment.initial_revenue_growth ?? null)} · margin {percent(segment.target_gross_margin ?? segment.target_operating_margin ?? null)}</p></div>)}</div></div>}</div>}
      <div className={cn(panel, 'p-6')}><p className="mb-3 text-[11px] font-semibold uppercase tracking-[.16em] text-[var(--app-muted)]">Source filing</p><div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm"><span className="font-semibold">{data.source_financial_statement.form}</span><span className="text-[var(--app-muted)]">period end {data.source_financial_statement.period_end}</span><span className="text-[var(--app-muted)]">filed {data.source_financial_statement.filed_date}</span><a href={data.source_financial_statement.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold underline decoration-dotted">SEC filing <ExternalLink className="h-3.5 w-3.5" /></a></div><p className="mt-4 text-[11px] leading-relaxed text-[var(--app-muted)]">Derived values, assumptions, warnings, and filing attribution only—no raw vendor prices or recommendations. Valuation date {data.valuation_date}.</p></div>
    </div>}
  </div>
}
