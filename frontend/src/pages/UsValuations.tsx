import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  BarChart3,
  Check,
  ChevronDown,
  ExternalLink,
  Heart,
  Info,
  RotateCcw,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react'
import {
  addHolding,
  calculateUsValuation,
  getUsValuation,
  getUsValuationCalculator,
  getUsValuationHistory,
  listHoldings,
  listUsValuations,
} from '@/lib/api'
import type {
  UsCalculatorField,
  UsCalculatorResult,
  UsCalculatorView,
  UsModelResult,
  UsValuation,
  UsValuationSummary,
  UsValuationHistory,
} from '@/lib/types'
import { cn } from '@/lib/utils'
import { ValuationSwipeDeck } from '@/components/ValuationSwipeDeck'
import { CompanyLogo } from '@/components/CompanyLogo'

type Scenario = 'low' | 'base' | 'high'

const usd = (value: number | null | undefined, digits = 2) =>
  Number.isFinite(value)
    ? new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(value as number)
    : '—'

const pct = (value: number | null | undefined, digits = 1) =>
  Number.isFinite(value) ? `${((value as number) * 100).toFixed(digits)}%` : '—'

const humanize = (value: string | null | undefined) =>
  (value ?? '').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

function modelValue(result: UsModelResult | undefined) {
  return result?.conditional_value_per_share ?? result?.intrinsic_value_per_share ?? null
}

function modelLabel(model: string | null | undefined) {
  const labels: Record<string, string> = {
    fcff_dcf: 'DCF valuation',
    residual_income: 'Residual income',
    ddm: 'Dividend valuation',
    fcfe_dcf: 'Equity cash flow',
    ffo: 'FFO valuation',
    conditional_estimate: 'Intrinsic valuation',
    practical_fcff: 'Cash flow valuation',
  }
  const normalized = model ?? ''
  if (labels[normalized]) return labels[normalized]
  if (normalized.includes('residual')) return 'Residual income'
  if (normalized.includes('ffo') || normalized.includes('affo')) return 'FFO valuation'
  if (normalized.includes('ddm') || normalized.includes('dividend')) return 'Dividend valuation'
  if (normalized.includes('fcfe')) return 'Equity cash flow'
  if (normalized.includes('fcff') || normalized.includes('dcf')) return 'Cash flow valuation'
  return humanize(model)
}

function availabilityLabel(data: UsValuation) {
  if (data.availability_type === 'not_available') return 'Valuation unavailable'
  if (data.availability_type === 'conditional_estimate') return 'Conditional estimate'
  return 'Reviewed baseline'
}

function SliderControl({
  field,
  value,
  onChange,
}: {
  field: UsCalculatorField
  value: number
  onChange: (value: number) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const display = field.unit === 'percent'
    ? `${(value * 100).toFixed(2)}%`
    : field.unit === 'multiple'
      ? `${value.toFixed(2)}×`
      : field.unit === 'years'
        ? `${value} yrs`
        : value.toFixed(2)
  const progress = ((value - field.min) / (field.max - field.min || 1)) * 100
  const numericValue = field.unit === 'percent' ? value * 100 : value
  const numericMin = field.unit === 'percent' ? field.min * 100 : field.min
  const numericMax = field.unit === 'percent' ? field.max * 100 : field.max
  const numericStep = field.unit === 'percent' ? field.step * 100 : field.step
  return (
    <label className="assumption-control block border-b border-[var(--app-border)] last:border-0">
      <div className="assumption-control-heading flex items-center justify-between gap-3">
        <span className="text-sm font-semibold">{field.label}</span>
        <div className="assumption-value-field">
          <input
            type="number"
            aria-label={`${field.label} value`}
            min={numericMin}
            max={numericMax}
            step={numericStep}
            value={editing ? draft : field.unit === 'percent' ? numericValue.toFixed(2) : Number(numericValue.toFixed(4))}
            onFocus={() => {
              setEditing(true)
              setDraft(field.unit === 'percent' ? numericValue.toFixed(2) : String(Number(numericValue.toFixed(4))))
            }}
            onBlur={() => setEditing(false)}
            onChange={(event) => {
              setDraft(event.target.value)
              if (event.target.value.trim() === '') return
              const next = Number(event.target.value)
              if (!Number.isFinite(next)) return
              onChange(field.unit === 'percent' ? next / 100 : next)
            }}
            className="assumption-number"
          />
          <span className="assumption-unit" aria-hidden="true">
            {field.unit === 'percent' ? '%' : field.unit === 'years' ? 'y' : ''}
          </span>
        </div>
      </div>
      <input
        type="range"
        min={field.min}
        max={field.max}
        step="any"
        value={value}
        aria-label={field.label}
        aria-valuetext={display}
        onChange={(event) => onChange(Number(event.target.value))}
        onKeyDown={(event) => {
          const direction = event.key === 'ArrowRight' || event.key === 'ArrowUp' ? 1 : event.key === 'ArrowLeft' || event.key === 'ArrowDown' ? -1 : 0
          if (direction) {
            event.preventDefault()
            onChange(Math.max(field.min, Math.min(field.max, value + direction * field.step)))
          }
        }}
        style={{ '--range-progress': `${Math.max(0, Math.min(100, progress))}%` } as React.CSSProperties}
        className="finsight-range w-full"
      />
      <div className="mt-2 flex justify-between text-[10px] font-medium text-[var(--app-muted)]">
        <span>{field.unit === 'percent' ? pct(field.min, 1) : field.min}</span>
        <span>{field.unit === 'percent' ? pct(field.max, 1) : field.max}</span>
      </div>
    </label>
  )
}

function EvidenceHealth({ rows }: { rows: UsValuation['evidence_health'] }) {
  const icons = [ShieldCheck, BarChart3, Sparkles, Check]
  return (
    <section className="rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,.04)] sm:p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">Evidence health</p>
          <h2 className="mt-1 text-lg font-semibold tracking-[-.025em]">How dependable is this baseline?</h2>
        </div>
        <span title="These scores describe valuation evidence quality, not company operating health.">
          <Info className="h-4 w-4 text-[var(--app-muted)]" />
        </span>
      </div>
      <div className="space-y-3">
        {!rows?.length && <p className="rounded-2xl bg-[var(--app-subtle)] p-4 text-sm leading-relaxed text-[var(--app-muted)]">This catalog does not publish a score breakdown. See Source filing for the available evidence.</p>}
        {(rows ?? []).map((row, index) => {
          const Icon = icons[index] ?? Check
          return (
            <div key={row.key} className="grid grid-cols-[42px_1fr_auto] items-center gap-3 rounded-2xl border border-[var(--app-border)] bg-[#fbfbfc] px-3 py-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-white shadow-sm">
                <Icon className="h-5 w-5" />
              </span>
              <div>
                <p className="text-sm font-semibold">{row.label}</p>
                <p className="mt-0.5 text-[10px] text-[var(--app-muted)]">{row.methodology_version}</p>
              </div>
              <div className="text-right">
                <strong className="text-xl tabular-nums">{row.score ?? '—'}<small className="text-[10px] font-medium text-[var(--app-muted)]"> /100</small></strong>
                <p className={cn(
                  'health-band text-[10px] font-bold',
                  row.band === 'High' ? 'text-[#168353]' : row.band === 'Medium' ? 'text-[#2469c8]' : 'text-[#9a6b12]',
                )}>{row.band}</p>
              </div>
            </div>
          )
        })}
      </div>
      <p className="mt-4 text-[10px] leading-relaxed text-[var(--app-muted)]">
        Evidence-quality scores summarize source, accounting, scenario, and model review. They do not claim to measure profitability or financial strength.
      </p>
    </section>
  )
}

function ModelCards({ data, override }: { data: UsValuation; override?: number }) {
  return (
    <section className="grid gap-4 sm:grid-cols-2">
      {Object.entries(data.models ?? {}).map(([key, result]) => {
        const primary = key === data.model_policy.primary || key === data.primary_valuation_method
        const value = primary && Number.isFinite(override) ? override : modelValue(result)
        return (
          <article key={key} className="rounded-[22px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_30px_rgba(15,23,42,.04)]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">{primary ? 'Primary model' : 'Cross-check'}</p>
                <h3 className="mt-1 text-sm font-semibold">{modelLabel(key)}</h3>
              </div>
              <span className="rounded-full bg-[#f1f2f4] px-2 py-1 text-[9px] font-bold uppercase tracking-[.08em] text-[var(--app-muted)]">
                {humanize(result.publication_state ?? 'reviewed')}
              </span>
            </div>
            <strong className="mt-6 block text-3xl font-semibold tracking-[-.04em] tabular-nums">{usd(value)}</strong>
            <p className="mt-1 text-xs text-[var(--app-muted)]">intrinsic value per share</p>
            {(result.warnings?.length ?? 0) > 0 && (
              <p className="mt-4 line-clamp-2 text-[11px] leading-relaxed text-[var(--app-muted)]">{result.warnings[0]}</p>
            )}
          </article>
        )
      })}
    </section>
  )
}

export default function UsValuations() {
  const { ticker: routeTicker = 'AAPL' } = useParams()
  const navigate = useNavigate()
  const ticker = routeTicker.toUpperCase()
  const requestVersion = useRef(0)
  const [list, setList] = useState<UsValuationSummary[]>([])
  const [catalogInfo, setCatalogInfo] = useState<{ version: string; batches: number[] } | null>(null)
  const [data, setData] = useState<UsValuation | null>(null)
  const [calculator, setCalculator] = useState<UsCalculatorView | null>(null)
  const [history, setHistory] = useState<UsValuationHistory | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [valuesByCase, setValuesByCase] = useState<Record<Scenario, Record<string, number>>>({ low: {}, base: {}, high: {} })
  const [resultsByCase, setResultsByCase] = useState<Partial<Record<Scenario, UsCalculatorResult>>>({})
  const [scenario, setScenario] = useState<Scenario>('base')
  const values = valuesByCase[scenario]
  const calculated = resultsByCase[scenario]
  const selectedDefaults = calculator?.scenario_presets?.[scenario] ?? (scenario === 'base' ? calculator?.defaults : undefined)
  const canEditCase = !!calculator?.can_calculate && !!selectedDefaults

  function setValues(update: Record<string, number> | ((current: Record<string, number>) => Record<string, number>)) {
    setValuesByCase(current => ({ ...current, [scenario]: typeof update === 'function' ? update(current[scenario]) : update }))
  }

  function selectCase(next: Scenario) {
    requestVersion.current++
    setScenario(next)
    setCalculatorError(null)
    setSavedMessage(null)
  }
  const [advanced, setAdvanced] = useState(false)
  const [manualPrice, setManualPrice] = useState('')
  const [held, setHeld] = useState(false)
  const [adding, setAdding] = useState(false)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [calculatorError, setCalculatorError] = useState<string | null>(null)

  useEffect(() => {
    listUsValuations()
      .then((result) => {
        setList(result.items)
        setCatalogInfo({ version: result.catalog_version, batches: result.included_batches })
        if (!result.items.some((company) => company.ticker === ticker)) navigate('/valuation/AAPL', { replace: true })
      })
      .catch(() => setList([]))
  }, [navigate, ticker])

  useEffect(() => {
    let live = true
    setLoading(true)
    setError(null)
    requestVersion.current++
    setResultsByCase({})
    setCalculator(null)
    setManualPrice('')
    setScenario('base')
    setAdvanced(false)
    setSavedMessage(null)
    Promise.all([getUsValuation(ticker), getUsValuationCalculator(ticker), listHoldings()])
      .then(([detail, view, holdings]) => {
        if (!live) return
        setData(detail)
        setCalculator(view)
        setValuesByCase({
          low: { ...(view.scenario_presets?.low ?? {}) },
          base: { ...view.defaults },
          high: { ...(view.scenario_presets?.high ?? {}) },
        })
        setHeld(holdings.some((holding) => holding.market === 'US' && holding.ticker === ticker))
      })
      .catch((caught: Error) => live && setError(caught.message))
      .finally(() => live && setLoading(false))
    return () => { live = false; requestVersion.current++ }
  }, [ticker])

  const overrides = useMemo(() => values, [values])
  useEffect(() => {
    let live = true
    setHistory(null); setHistoryError(null)
    getUsValuationHistory(ticker).then(result => { if (live) setHistory(result) })
      .catch((caught: Error) => { if (live) setHistoryError(caught.message) })
    return () => { live = false }
  }, [ticker])
  useEffect(() => {
    if (!calculator?.can_calculate) return
    const version = ++requestVersion.current
    const timer = window.setTimeout(() => {
      calculateUsValuation(ticker, {
        overrides,
        scenario,
        baseline_version: calculator.baseline_version,
        recipe_version: calculator.recipe_version,
        ...(Number(manualPrice) > 0 ? { manual_price: Number(manualPrice) } : {}),
      })
        .then((result) => {
          if (requestVersion.current !== version) return
          setResultsByCase(current => ({ ...current, [scenario]: result }))
          setCalculatorError(null)
        })
        .catch((caught: Error) => {
          if (requestVersion.current !== version) return
          setCalculatorError(caught.message)
        })
    }, 250)
    return () => { window.clearTimeout(timer); requestVersion.current++ }
  }, [calculator, manualPrice, overrides, ticker, values, scenario])

  const range = data ? {
    low: resultsByCase.low?.result.low ?? data.scenario_range.low,
    base: resultsByCase.base?.result.base ?? data.scenario_range.base,
    high: resultsByCase.high?.result.high ?? data.scenario_range.high,
  } : undefined
  const selectedValue = range?.[scenario]
  const baseValue = range?.base
  const overlappingCases = range?.low != null && range.base != null && range.high != null
    && (range.low > range.base || range.base > range.high)
  const comparison = calculated?.manual_price === (Number(manualPrice) > 0 ? Number(manualPrice) : null) ? calculated?.comparison : null
  const scenarioLabel = scenario === 'low' ? 'Bear case' : scenario === 'high' ? 'Bull case' : 'Base case'
  const barPosition = (() => {
    if (Number.isFinite(selectedValue) && Number.isFinite(range?.low) && Number.isFinite(range?.high) && (range?.high ?? 0) > (range?.low ?? 0)) {
      return 12 + (((selectedValue as number) - (range?.low as number)) / ((range?.high as number) - (range?.low as number))) * 76
    }
    return scenario === 'low' ? 18 : scenario === 'high' ? 82 : 50
  })()
  const dirty = selectedDefaults
    ? Object.entries(values).some(([key, value]) => value !== Number(selectedDefaults[key]))
    : false
  const primaryModel = data?.primary_valuation_method ?? data?.model_policy.primary
  const primaryResult = data
    ? data.models[primaryModel ?? ''] ?? data.models[data.model_policy.primary]
    : undefined

  function reset() {
    if (!selectedDefaults) return
    requestVersion.current++
    setValues({ ...selectedDefaults })
    setManualPrice('')
    setResultsByCase(current => { const next = { ...current }; delete next[scenario]; return next })
    setCalculatorError(null)
    setSavedMessage(null)
  }

  async function saveScenario() {
    if (!canEditCase) return
    const version = requestVersion.current
    try {
      const result = await calculateUsValuation(ticker, {
        overrides,
        scenario,
        baseline_version: calculator?.baseline_version,
        recipe_version: calculator?.recipe_version,
        ...(Number(manualPrice) > 0 ? { manual_price: Number(manualPrice) } : {}),
        save: true,
      })
      if (requestVersion.current !== version) return
      if (result.selected_scenario === scenario) setResultsByCase(current => ({ ...current, [scenario]: result }))
      setSavedMessage(`Saved scenario #${result.saved_id}`)
      setCalculatorError(null)
    } catch (caught) {
      if (requestVersion.current !== version) return
      setCalculatorError(caught instanceof Error ? caught.message : 'Could not save scenario')
    }
  }

  async function addToPortfolio() {
    if (held || !data) return
    setAdding(true)
    try {
      await addHolding(ticker, 'US')
      setHeld(true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not add to portfolio')
    } finally {
      setAdding(false)
    }
  }

  if (loading) {
    return <div className="space-y-5"><div className="h-48 animate-pulse rounded-[26px] bg-white" /><div className="grid gap-5 md:grid-cols-2"><div className="h-72 animate-pulse rounded-[26px] bg-white" /><div className="h-72 animate-pulse rounded-[26px] bg-white" /></div></div>
  }

  if (error || !data) {
    return <div className="rounded-[24px] border border-[#f2c9cf] bg-[#fff7f8] p-6 text-sm text-[#a02f43]"><AlertCircle className="mb-3 h-5 w-5" />{error ?? 'Valuation unavailable.'}</div>
  }

  const unavailable = data.availability_type === 'not_available'
  const explanation = data.review?.errors?.[0] ?? data.review?.warnings?.[0] ?? data.model_policy.reason

  const assumptionsPanel = (
    <section className="assumptions-panel rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,.04)] sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            <h2 className="text-lg font-semibold tracking-[-.025em]">Key assumptions <span className="ml-2 text-xs font-medium text-[var(--app-muted)]">{scenarioLabel}</span></h2>
            <Info className="h-4 w-4 text-[var(--app-muted)]" />
          </div>
          <p className="mt-2 max-w-xl text-xs leading-5 text-[var(--app-muted)]">{calculator?.scenario_preset_note ?? 'Adjust governed inputs; filing facts and the capital bridge stay locked.'}</p>
        </div>
        <button type="button" onClick={reset} disabled={!canEditCase} className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-[var(--app-muted)] hover:bg-[var(--app-subtle)] hover:text-[var(--app-text)] disabled:opacity-40">
          <RotateCcw className="h-4 w-4" /> Reset
        </button>
      </div>
      {!canEditCase ? (
        <p className="mt-6 rounded-2xl bg-[var(--app-subtle)] p-4 text-sm text-[var(--app-muted)]">{calculator?.can_calculate ? `Verified ${scenarioLabel.toLowerCase()} inputs are not available for this company. Select Base case to use the calculator; this case's published value remains visible.` : 'Assumption controls are unavailable because this batch result has no confirmed numeric baseline.'}</p>
      ) : (
        <>
          <div className="assumption-controls">
            {calculator!.editable_assumptions.slice(0, 3).map((field) => (
              <SliderControl key={`${scenario}-${field.key}`} field={field} value={values[field.key] ?? field.value} onChange={(value) => { setValues((current) => ({ ...current, [field.key]: value })); setSavedMessage(null) }} />
            ))}
          </div>
          {calculator!.editable_assumptions.length > 3 && (
            <div className="border-t border-[var(--app-border)] pt-3">
              <button type="button" onClick={() => setAdvanced((open) => !open)} className="flex w-full items-center justify-between rounded-xl px-2 py-2 text-sm font-semibold hover:bg-[var(--app-subtle)]">
                Advanced assumptions
                <ChevronDown className={cn('h-4 w-4 transition-transform', advanced && 'rotate-180')} />
              </button>
              {advanced && calculator!.editable_assumptions.slice(3).map((field) => (
                <SliderControl key={`${scenario}-${field.key}`} field={field} value={values[field.key] ?? field.value} onChange={(value) => { setValues((current) => ({ ...current, [field.key]: value })); setSavedMessage(null) }} />
              ))}
            </div>
          )}
          <div className="assumptions-actions flex flex-wrap items-end justify-between gap-3 border-t border-[var(--app-border)]">
            <label className="grid gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">User-entered market price</span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={manualPrice}
                onChange={(event) => setManualPrice(event.target.value)}
                placeholder="Optional"
                className="h-11 w-52 rounded-xl border border-[var(--app-border)] bg-[#fbfbfc] px-3 text-sm outline-none focus:border-[#9ca3af]"
              />
              <small className="text-[10px] font-normal text-[var(--app-muted)]">Session-only; never treated as a live quote.</small>
            </label>
            <button type="button" onClick={saveScenario} className="inline-flex h-11 items-center gap-2 rounded-xl bg-[#111318] px-4 text-sm font-semibold text-white shadow-sm hover:-translate-y-0.5">
              <Save className="h-4 w-4" /> Save scenario
            </button>
          </div>
          {calculatorError && <p className="mt-3 rounded-xl bg-[#fff3f4] px-3 py-2 text-xs text-[#b4233c]">{calculatorError}</p>}
          {savedMessage && <p className="mt-3 rounded-xl bg-[#eef8f2] px-3 py-2 text-xs font-semibold text-[#16794b]">{savedMessage}</p>}
        </>
      )}
    </section>
  )

  return (
    <div className="valuation-workspace">
      <section className="company-identity overflow-hidden rounded-[28px] border border-[var(--app-border)] bg-white shadow-[0_18px_55px_rgba(15,23,42,.05)]">
        <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-7">
          <div className="flex min-w-0 items-center gap-4">
            <span className="company-monogram grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-[var(--app-border)] bg-[#fafafa] text-sm font-black shadow-sm">
              <CompanyLogo ticker={ticker} />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-semibold tracking-[-.045em]">{data.issuer.issuer_name}</h1>
                <span className={cn(
                  'company-status rounded-full px-2.5 py-1 text-[9px] font-bold uppercase tracking-[.09em]',
                  unavailable ? 'bg-[#f1f2f4] text-[var(--app-muted)]' : data.availability_type === 'conditional_estimate' ? 'bg-[#fff6df] text-[#8a5c08]' : 'bg-[#eef8f2] text-[#16794b]',
                )}>{availabilityLabel(data)}</span>
              </div>
              <p className="mt-1 text-sm text-[var(--app-muted)]">US · {ticker} · {humanize(data.issuer.finsight_sector)}{data.catalog?.batch != null && ` · Batch ${data.catalog.batch}`}</p>
              <div className="mt-3 inline-flex rounded-xl border border-[var(--app-border)] bg-[#fbfbfc] p-1 text-[10px] font-bold">
                <span className="rounded-lg bg-[#111318] px-3 py-1.5 text-white">US</span>
                <Link to="/pse/AP" className="rounded-lg px-3 py-1.5 text-[var(--app-muted)] hover:text-[var(--app-text)]">PH</Link>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={addToPortfolio}
            disabled={held || adding}
            className={cn(
              'portfolio-action inline-flex h-11 items-center gap-2 rounded-xl border px-4 text-sm font-semibold shadow-sm',
              held ? 'border-[#cfe9da] bg-[#eef8f2] text-[#16794b]' : 'border-[var(--app-border)] bg-white hover:-translate-y-0.5 hover:shadow-md',
            )}
          >
            {held ? <Check className="h-4 w-4" /> : <Heart className="h-4 w-4" />}
            {held ? 'In portfolio' : adding ? 'Adding…' : 'Add to portfolio'}
          </button>
        </div>
      </section>

      {data.freshness?.outcome === 'acquisition_failed' && <p role="status" className="rounded-2xl border border-[#ecd9a7] bg-[#fff9e8] p-4 text-sm text-[#805c13]">The latest filing refresh failed. This is the previous dated estimate, not a successfully refreshed valuation.</p>}
      {overlappingCases && <p role="status" className="rounded-2xl border border-[#ecd9a7] bg-[#fff9e8] p-4 text-sm text-[#805c13]">Your separately edited cases now overlap. Adjust or reset their assumptions before treating them as a bear-to-bull range.</p>}
      {unavailable ? (
        <section className="rounded-[26px] border border-[var(--app-border)] bg-white p-7 shadow-[0_16px_45px_rgba(15,23,42,.05)]">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#f1f2f4]"><AlertCircle className="h-5 w-5" /></span>
          <p className="mt-6 text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">No reliable numeric baseline</p>
          <h2 className="mt-2 max-w-2xl text-3xl font-semibold tracking-[-.04em]">FinSight withheld this value instead of filling the gap with a guess.</h2>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--app-muted)]">{explanation}</p>
        </section>
      ) : (
        <ValuationSwipeDeck key={ticker} date={data.valuation_date} ticker={ticker} labels={['Summary', modelLabel(primaryModel) || 'Primary model', 'Cross-checks', 'Key assumptions', 'Source filing']}>
          <div className="valuation-overview">
            <article className="intrinsic-hero rounded-[26px] border border-[var(--app-border)] bg-white p-6 shadow-[0_16px_45px_rgba(15,23,42,.05)] sm:p-7">
              <div className="flex items-center gap-2 text-sm font-semibold">
                Intrinsic value ({scenarioLabel})
                <Info className="h-4 w-4 text-[var(--app-muted)]" />
              </div>
              <strong key={scenario} className="value-reveal mt-7 block text-5xl font-semibold tracking-[-.055em] tabular-nums sm:text-6xl">{usd(selectedValue)}</strong>
              {comparison ? (
                <div className={cn(
                  'comparison-badge mt-5 inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold',
                  comparison.verdict === 'overvalued' ? 'bg-[#fff0f2] text-[#d12e4f]' : comparison.verdict === 'undervalued' ? 'bg-[#edf9f2] text-[#168353]' : 'bg-[#f1f2f4]',
                )}>
                  {comparison.verdict === 'overvalued' ? <ArrowDown className="h-4 w-4" /> : <ArrowUp className="h-4 w-4" />}
                  {comparison.label}
                </div>
              ) : (
                <p className="mt-5 text-sm text-[var(--app-muted)]">Enter a market price below to compare it with this valuation.</p>
              )}
              <p className="mt-7 text-sm leading-7 text-[var(--app-muted)]">
                {dirty ? 'Your edited' : 'FinSight’s'} {scenarioLabel.toLowerCase()} for {data.issuer.issuer_name} is {usd(selectedValue)} per share. This is a filing-based educational estimate, not a recommendation.
              </p>
              <div className="mt-7 grid grid-cols-2 gap-3 border-t border-[var(--app-border)] pt-5">
                <div className="rounded-2xl bg-[#fafafa] p-4">
                  <p className="text-[10px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">Primary model</p>
                  <strong className="mt-2 block text-lg">{modelLabel(primaryModel)}</strong>
                  <span className="mt-1 block text-sm tabular-nums">{usd(dirty ? baseValue : modelValue(primaryResult))}</span>
                </div>
                <div className="rounded-2xl bg-[#fafafa] p-4">
                  <p className="text-[10px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">Reliability</p>
                  <strong className="mt-2 block text-lg">{data.reliability?.label ?? 'Reviewed'}</strong>
                  <span className="mt-1 block text-xs text-[var(--app-muted)]">Source-bounded baseline</span>
                </div>
              </div>
              <div className="overview-context">
                <div><span>{dirty ? 'Your bear–bull range' : 'Bear–bull range'}</span><strong>{usd(range?.low)} – {usd(range?.high)}</strong></div>
                <div><span>Financial period ending</span><strong>{data.source_financial_statement.period_end}</strong></div>
                {data.source_financial_statement.url && <div><span>Source document</span><a href={data.source_financial_statement.url} target="_blank" rel="noreferrer">{data.source_financial_statement.form} filing <ExternalLink size={12} /></a></div>}
              </div>
            </article>

            <article className="rounded-[26px] border border-[var(--app-border)] bg-white p-6 shadow-[0_16px_45px_rgba(15,23,42,.05)] sm:p-7">
              <div className="flex items-center gap-2 text-sm font-semibold">Valuation summary <Info className="h-4 w-4 text-[var(--app-muted)]" /></div>
              <p className="mt-7 text-xs font-medium text-[var(--app-muted)]">Intrinsic value ({scenarioLabel})</p>
              <strong className="mt-1 block text-3xl font-semibold tracking-[-.04em] tabular-nums">{usd(selectedValue)}</strong>
              <div className="mt-7 h-3 overflow-hidden rounded-full bg-[#e5e7eb]">
                <span className="valuation-gauge-track block h-full rounded-full" style={{ width: '100%' }} />
              </div>
              <div className="relative mt-2 h-5">
                <span
                  className="absolute top-0 h-4 w-1.5 -translate-x-1/2 rounded-full bg-[#111318] transition-[left] duration-300"
                  style={{ left: `${Math.max(4, Math.min(96, barPosition))}%` }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div><strong className="text-xs">Undervalued</strong><span className="mt-1 block text-[10px] text-[var(--app-muted)]">Below intrinsic value</span></div>
                <div><strong className="text-xs">Fair value</strong><span className="mt-1 block text-[10px] text-[var(--app-muted)]">Around intrinsic value</span></div>
                <div><strong className="text-xs">Overvalued</strong><span className="mt-1 block text-[10px] text-[var(--app-muted)]">Above intrinsic value</span></div>
              </div>
              <div className="mt-8 grid grid-cols-3 gap-3">
                {(['low', 'base', 'high'] as const).map((key) => (
                  <button
                    type="button"
                    key={key}
                    onClick={() => selectCase(key)}
                    aria-pressed={scenario === key}
                    className={cn(
                      'scenario-button rounded-xl border border-[var(--app-border)] px-3 py-3 text-xs font-semibold capitalize',
                      scenario === key && 'border-[#111318] bg-[#111318] text-white shadow-md',
                    )}
                  >
                    <span>{key === 'low' ? 'Bear case' : key === 'high' ? 'Bull case' : 'Base case'}</span>
                    <strong>{usd(range?.[key])}</strong>
                  </button>
                ))}
              </div>
              <label className="mt-6 block border-t border-[var(--app-border)] pt-5">
                <span className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">Manual market price</span>
                <div className="mt-2 flex items-center rounded-xl border border-[var(--app-border)] bg-[#fafafa] px-3 focus-within:border-[#9ca3af]">
                  <span className="text-sm text-[var(--app-muted)]">$</span>
                  <input type="number" min="0.01" step="0.01" value={manualPrice} onChange={(event) => setManualPrice(event.target.value)} placeholder="User-entered, session only" className="h-11 w-full bg-transparent px-2 text-sm outline-none" />
                </div>
              </label>
            </article>
              {assumptionsPanel}
              <EvidenceHealth rows={data.evidence_health} />
          </div>

            <div className="space-y-5">
              <ModelCards data={data} override={dirty ? baseValue : undefined} />
              <section className="rounded-[24px] border border-[var(--app-border)] bg-white p-6 text-sm leading-7 text-[var(--app-muted)]">
                <strong className="block text-[var(--app-text)]">Why this model</strong>
                <p className="mt-2">{data.model_policy.reason}</p>
              </section>
            </div>

            <section className="grid gap-5 md:grid-cols-[1.05fr_.95fr]">
              <ModelCards data={data} override={dirty ? baseValue : undefined} />
              <EvidenceHealth rows={data.evidence_health} />
            </section>

            <section className="grid gap-5 md:grid-cols-[1.05fr_.95fr]">
              {assumptionsPanel}
              <article className="rounded-[24px] border border-[var(--app-border)] bg-white p-6 shadow-[0_12px_34px_rgba(15,23,42,.04)]">
                <p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">Governed baseline</p>
                <div className="mt-4 divide-y divide-[var(--app-border)]">
                  {Object.entries(data.public_assumptions ?? {}).filter(([, value]) => typeof value === 'number' || typeof value === 'string').slice(0, 10).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between gap-4 py-3 text-xs">
                      <span className="text-[var(--app-muted)]">{humanize(key)}</span>
                      <strong className="text-right tabular-nums">{typeof value === 'number' && Math.abs(value) < 1 ? pct(value) : String(value)}</strong>
                    </div>
                  ))}
                </div>
              </article>
            </section>
          <section className="rounded-[24px] border border-[var(--app-border)] bg-white p-6 shadow-[0_12px_34px_rgba(15,23,42,.04)]">
            <p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">Source filing</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-.035em]">The evidence behind this baseline.</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--app-muted)]">The published valuation keeps issuer identity, filing period, assumptions, warnings, and provenance visible alongside the model output.</p>
            {(data.normalization_explanation || data.public_assumptions?.normalization_basis) && <div className="mt-4 rounded-2xl bg-[#fafafa] p-4 text-sm leading-7 text-[var(--app-muted)]">
              <p className="font-semibold text-[var(--app-text)]">How the starting figures are normalized</p>
              <p>{data.normalization_explanation || `Recorded normalization method: ${humanize(data.public_assumptions.normalization_basis!)}.`}</p>
            </div>}
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-[#fafafa] p-4"><span className="text-[10px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">Form</span><strong className="mt-2 block">{data.source_financial_statement.form}</strong></div>
              <div className="rounded-2xl bg-[#fafafa] p-4"><span className="text-[10px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">Period end</span><strong className="mt-2 block">{data.source_financial_statement.period_end}</strong></div>
              <div className="rounded-2xl bg-[#fafafa] p-4"><span className="text-[10px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">Filed</span><strong className="mt-2 block">{data.source_financial_statement.filed_date}</strong></div>
            </div>
            <p className="mt-3 text-xs text-[var(--app-muted)]">Evidence cutoff: {data.dates?.evidence_cutoff || data.valuation_date}{data.assumption_date ? ` · Assumptions dated: ${data.assumption_date}` : ''}{data.model_version ? ` · Model: ${data.model_version}` : ''}</p>
            {data.source_financial_statement.url && <a href={data.source_financial_statement.url} target="_blank" rel="noreferrer" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold underline decoration-dotted">Open SEC filing <ExternalLink className="h-4 w-4" /></a>}
            <details className="mt-6 border-t border-[var(--app-border)] pt-4">
              <summary className="cursor-pointer text-sm font-semibold">Dated valuation history</summary>
              <p className="mt-2 text-xs text-[var(--app-muted)]">Prior estimates retain their original dates and assumptions.</p>
              {historyError ? <p className="mt-3 text-sm text-[#b4233c]">History could not be loaded: {historyError}</p> : history ? <ul className="mt-3 space-y-2 text-sm">{history.items.map(item => <li key={item.catalog_version}>{item.valuation_date} · {item.availability_type === 'not_available' ? 'Not available' : `${usd(item.scenario_range.low)} / ${usd(item.scenario_range.base)} / ${usd(item.scenario_range.high)}`} · filing period {item.source_financial_statement.period_end}</li>)}</ul> : <p className="mt-3 text-sm">Loading history…</p>}
            </details>
          </section>
        </ValuationSwipeDeck>
      )}

      <footer className="rounded-[20px] border border-[var(--app-border)] bg-white px-5 py-4 text-center text-[10px] leading-relaxed text-[var(--app-muted)]">
        <span className="font-semibold text-[var(--app-text)]">FinSight catalog {data.catalog?.catalog_version ?? catalogInfo?.version}</span>
        {catalogInfo?.batches.length ? ` · ${catalogInfo.batches.length} included batches` : ''}{' · '}Valuation date {data.valuation_date}
        {data.source_financial_statement?.url && (
          <a href={data.source_financial_statement.url} target="_blank" rel="noreferrer" className="ml-2 inline-flex items-center gap-1 font-semibold text-[var(--app-text)] underline decoration-dotted">
            Source filing <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </footer>
      <p className="text-center text-[10px] text-[var(--app-muted)]">{list.length} companies in this catalog.</p>
    </div>
  )
}
