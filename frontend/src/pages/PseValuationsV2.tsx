import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertCircle, ArrowDown, ArrowUp, ExternalLink, Heart, Info, RotateCcw, Save, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import { addHolding, calculatePseValuation, getPseValuation, getPseValuationCalculator, getPseValuationHistory, listHoldings, listPseValuations } from '../lib/api'
import type { PseCalculatorField, PseCalculatorResult, PseCalculatorView, PseValuation, PseValuationHistory } from '../lib/types'
import { CompanyLogo } from '@/components/CompanyLogo'
import { ValuationSwipeDeck } from '@/components/ValuationSwipeDeck'
import { cn } from '@/lib/utils'

type Scenario = 'low' | 'base' | 'high'

const peso = (value: number | null | undefined, digits = 2) => {
  if (!Number.isFinite(value)) return '—'
  const displayDigits = digits === 2 && Math.abs(value as number) > 0 && Math.abs(value as number) < 0.01 ? 4 : digits
  return new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP', minimumFractionDigits: displayDigits, maximumFractionDigits: displayDigits }).format(Number((value as number).toFixed(12)))
}
const pct = (value: number | null | undefined, digits = 1) => Number.isFinite(value) ? `${((value as number) * 100).toFixed(digits)}%` : '—'
const humanize = (value: string | null | undefined) => (value ?? '').replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase())

function SliderControl({ field, value, onChange }: { field: PseCalculatorField; value: number; onChange: (value: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const numericValue = field.unit === 'percent' ? value * 100 : value
  const numericMin = field.unit === 'percent' ? field.min * 100 : field.min
  const numericMax = field.unit === 'percent' ? field.max * 100 : field.max
  const numericStep = field.unit === 'percent' ? field.step * 100 : field.step
  const progress = ((value - field.min) / (field.max - field.min || 1)) * 100
  return <label className="assumption-control block border-b border-[var(--app-border)] last:border-0">
    <div className="assumption-control-heading flex items-center justify-between gap-3"><span className="text-sm font-semibold">{field.label}</span><div className="assumption-value-field"><input type="number" aria-label={`${field.label} value`} min={numericMin} max={numericMax} step={numericStep} value={editing ? draft : field.unit === 'percent' ? numericValue.toFixed(2) : Number(numericValue.toFixed(4))} onFocus={() => { setEditing(true); setDraft(field.unit === 'percent' ? numericValue.toFixed(2) : String(Number(numericValue.toFixed(4)))) }} onBlur={() => setEditing(false)} onChange={event => { setDraft(event.target.value); const next = Number(event.target.value); if (Number.isFinite(next)) onChange(field.unit === 'percent' ? next / 100 : next) }} className="assumption-number" /><span className="assumption-unit" aria-hidden="true">{field.unit === 'percent' ? '%' : field.unit === 'years' ? 'y' : ''}</span></div></div>
    <input type="range" min={field.min} max={field.max} step="any" value={value} aria-label={field.label} onChange={event => onChange(Number(event.target.value))} style={{ '--range-progress': `${Math.max(0, Math.min(100, progress))}%` } as React.CSSProperties} className="finsight-range w-full" />
    <div className="mt-2 flex justify-between text-[10px] font-medium text-[var(--app-muted)]"><span>{field.unit === 'percent' ? pct(field.min) : Number(field.min.toFixed(4))}</span><span>{field.unit === 'percent' ? pct(field.max) : Number(field.max.toFixed(4))}</span></div>
  </label>
}

export default function PseValuationsV2() {
  const { ticker: routeTicker = 'AP' } = useParams()
  const navigate = useNavigate()
  const ticker = routeTicker.toUpperCase()
  const requestVersion = useRef(0)
  const [data, setData] = useState<PseValuation | null>(null)
  const [calculator, setCalculator] = useState<PseCalculatorView | null>(null)
  const [history, setHistory] = useState<PseValuationHistory | null>(null)
  const [valuesByCase, setValuesByCase] = useState<Record<Scenario, Record<string, number>>>({ low: {}, base: {}, high: {} })
  const [resultsByCase, setResultsByCase] = useState<Partial<Record<Scenario, PseCalculatorResult>>>({})
  const [scenario, setScenario] = useState<Scenario>('base')
  const [manualPrice, setManualPrice] = useState('')
  const [held, setHeld] = useState(false)
  const [adding, setAdding] = useState(false)
  const [savedMessage, setSavedMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [calculatorError, setCalculatorError] = useState<string | null>(null)

  useEffect(() => { listPseValuations().then(result => { if (!result.items.some(company => company.ticker === ticker)) navigate('/pse/AP', { replace: true }) }).catch(() => {}) }, [navigate, ticker])
  useEffect(() => {
    let live = true
    setLoading(true); setError(null); setScenario('base'); setResultsByCase({}); setSavedMessage(null); setManualPrice(''); requestVersion.current++
    Promise.all([getPseValuation(ticker), getPseValuationCalculator(ticker), listHoldings(), getPseValuationHistory(ticker)])
      .then(([detail, view, holdings, dated]) => { if (!live) return; setData(detail); setCalculator(view); setHistory(dated); setValuesByCase({ low: { ...view.scenario_presets.low }, base: { ...view.scenario_presets.base }, high: { ...view.scenario_presets.high } }); setHeld(holdings.some(holding => holding.market === 'PH' && holding.ticker === ticker)) })
      .catch((caught: Error) => live && setError(caught.message)).finally(() => live && setLoading(false))
    return () => { live = false; requestVersion.current++ }
  }, [ticker])

  const values = valuesByCase[scenario]
  const selectedDefaults = calculator?.scenario_presets[scenario]
  const overrides = useMemo(() => values, [values])
  useEffect(() => {
    if (!calculator?.can_calculate || !selectedDefaults) return
    const version = ++requestVersion.current
    const timer = window.setTimeout(() => calculatePseValuation(ticker, { overrides, scenario, ...(Number(manualPrice) > 0 ? { manual_price: Number(manualPrice) } : {}) }).then(result => { if (version !== requestVersion.current) return; setResultsByCase(current => ({ ...current, [scenario]: result })); setCalculatorError(null) }).catch((caught: Error) => version === requestVersion.current && setCalculatorError(caught.message)), 250)
    return () => { window.clearTimeout(timer); requestVersion.current++ }
  }, [calculator, manualPrice, overrides, scenario, selectedDefaults, ticker])

  const baseline = calculator?.baseline_result
  const range = baseline ? { low: resultsByCase.low?.result.low ?? baseline.low, base: resultsByCase.base?.result.base ?? baseline.base, high: resultsByCase.high?.result.high ?? baseline.high } : undefined
  const calculated = resultsByCase[scenario]
  const selectedValue = range?.[scenario]
  const comparison = calculated?.manual_price === (Number(manualPrice) > 0 ? Number(manualPrice) : null) ? calculated.comparison : null
  const marketRelative = data?.availability_type === 'market_relative_only'
  const caseLabel = scenario === 'low' ? (marketRelative ? 'Low estimate' : 'Bear case') : scenario === 'high' ? (marketRelative ? 'High estimate' : 'Bull case') : 'Base case'
  const dirty = selectedDefaults ? Object.entries(values).some(([key, value]) => value !== Number(selectedDefaults[key])) : false
  function setValue(key: string, value: number) { setValuesByCase(current => ({ ...current, [scenario]: { ...current[scenario], [key]: value } })); setSavedMessage(null) }
  function selectCase(next: Scenario) { requestVersion.current++; setScenario(next); setCalculatorError(null); setSavedMessage(null) }
  function reset() { if (!selectedDefaults) return; requestVersion.current++; setValuesByCase(current => ({ ...current, [scenario]: { ...selectedDefaults } })); setManualPrice(''); setResultsByCase(current => { const next = { ...current }; delete next[scenario]; return next }); setCalculatorError(null); setSavedMessage(null) }
  async function saveScenario() { try { const result = await calculatePseValuation(ticker, { overrides, scenario, save: true, ...(Number(manualPrice) > 0 ? { manual_price: Number(manualPrice) } : {}) }); setResultsByCase(current => ({ ...current, [scenario]: result })); setSavedMessage(`Saved scenario #${result.saved_id}`) } catch (caught) { setCalculatorError(caught instanceof Error ? caught.message : 'Could not save scenario') } }
  async function addToPortfolio() { if (held) return; setAdding(true); try { await addHolding(ticker, 'PH'); setHeld(true) } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not add to portfolio') } finally { setAdding(false) } }

  if (loading) return <div className="space-y-5"><div className="h-48 animate-pulse rounded-[26px] bg-white" /><div className="h-96 animate-pulse rounded-[26px] bg-white" /></div>
  if (error || !data || !calculator) return <div className="rounded-[24px] border border-[#f2c9cf] bg-[#fff7f8] p-6 text-sm text-[#a02f43]"><AlertCircle className="mb-3 h-5 w-5" />{error ?? 'Valuation unavailable.'}</div>
  if (data.availability_type === 'not_available') return <div className="valuation-workspace">
    <section className="company-identity rounded-[28px] border border-[var(--app-border)] bg-white px-5 py-5 shadow-[0_18px_55px_rgba(15,23,42,.05)] sm:px-7">
      <div className="flex items-center gap-4"><span className="company-monogram grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-[var(--app-border)] bg-[#fafafa] text-sm font-black"><CompanyLogo ticker={ticker} /></span><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-semibold">{data.issuer.name}</h1><span className="company-status rounded-full bg-[#fff0f2] px-2.5 py-1 text-[9px] font-bold uppercase text-[#a02f43]">Blocked · unavailable</span></div><p className="mt-1 text-sm text-[var(--app-muted)]">PH · {ticker} · {data.subsector}</p><div className="mt-3 inline-flex rounded-xl border border-[var(--app-border)] bg-[#fbfbfc] p-1 text-[10px] font-bold"><Link to="/valuation/AAPL" className="rounded-lg px-3 py-1.5 text-[var(--app-muted)]">US</Link><span className="rounded-lg bg-[#111318] px-3 py-1.5 text-white">PH</span></div></div></div>
    </section>
    <ValuationSwipeDeck key={ticker} date={data.valuation_date} ticker={ticker} labels={['Summary', 'Why unavailable', 'Source evidence']}>
      <section className="rounded-[26px] border border-[var(--app-border)] bg-white p-7 shadow-[0_16px_45px_rgba(15,23,42,.05)]"><p className="text-sm font-semibold">Valuation unavailable</p><strong className="mt-7 block text-5xl font-semibold">—</strong><p className="mt-5 text-sm leading-7 text-[var(--app-muted)]">No current per-share value or calculator is published for {data.issuer.name}. {data.blocking_reasons[0]}</p><p className="mt-5 text-xs text-[var(--app-muted)]">Financial period {data.filing_period ?? 'under review'} · Publication state blocked</p></section>
      <Limitations data={data} />
      <section className="rounded-[24px] border border-[var(--app-border)] bg-white p-6"><h2 className="text-2xl font-semibold">Source evidence</h2><p className="mt-3 text-sm text-[var(--app-muted)]">These reviewed source links explain the blocked status; they do not imply a current valuation.</p><ul className="mt-5 grid gap-3 sm:grid-cols-2">{data.sources.map(source => <li key={source.document_id} className="rounded-2xl bg-[#fafafa] p-4 text-xs"><strong className="block">{source.label}</strong>{source.url && <a href={source.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 underline">Open source <ExternalLink className="h-3 w-3" /></a>}</li>)}</ul></section>
    </ValuationSwipeDeck>
    <footer className="rounded-[20px] border border-[var(--app-border)] bg-white px-5 py-4 text-center text-[10px] text-[var(--app-muted)]">FinSight catalog {data.catalog.catalog_version} · Valuation date {data.valuation_date} · {data.catalog.artifact_count} companies</footer>
  </div>
  if (!range) return <div className="rounded-[24px] border border-[#f2c9cf] bg-[#fff7f8] p-6 text-sm text-[#a02f43]"><AlertCircle className="mb-3 h-5 w-5" />Valuation unavailable.</div>

  const assumptionsPanel = <section className="assumptions-panel rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,.04)] sm:p-6">
    <div className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2"><SlidersHorizontal className="h-4 w-4" /><h2 className="text-lg font-semibold">Key assumptions <span className="ml-2 text-xs font-medium text-[var(--app-muted)]">{caseLabel}</span></h2></div><p className="mt-2 text-xs leading-5 text-[var(--app-muted)]">{calculator.scenario_preset_note}</p></div><button type="button" onClick={reset} className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold text-[var(--app-muted)] hover:bg-[var(--app-subtle)]"><RotateCcw className="h-4 w-4" /> Reset</button></div>
    <div className="assumption-controls">{calculator.editable_assumptions.map(field => <SliderControl key={`${scenario}-${field.key}`} field={field} value={values[field.key] ?? field.value} onChange={value => setValue(field.key, value)} />)}</div>
    <div className="assumptions-actions flex flex-wrap items-end justify-between gap-3 border-t border-[var(--app-border)]"><label className="grid gap-1.5"><span className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">User-entered market price</span><input type="number" min="0.01" step="0.01" value={manualPrice} onChange={event => setManualPrice(event.target.value)} placeholder="Optional" className="h-11 w-52 rounded-xl border border-[var(--app-border)] bg-[#fbfbfc] px-3 text-sm outline-none" /><small className="text-[10px] text-[var(--app-muted)]">Session-only; never treated as a live quote.</small></label><button type="button" onClick={saveScenario} className="inline-flex h-11 items-center gap-2 rounded-xl bg-[#111318] px-4 text-sm font-semibold text-white"><Save className="h-4 w-4" /> Save scenario</button></div>
    {calculatorError && <p className="mt-3 rounded-xl bg-[#fff3f4] px-3 py-2 text-xs text-[#b4233c]">{calculatorError}</p>}{savedMessage && <p className="mt-3 rounded-xl bg-[#eef8f2] px-3 py-2 text-xs font-semibold text-[#16794b]">{savedMessage}</p>}
  </section>

  return <div className="valuation-workspace">
    <section className="company-identity overflow-hidden rounded-[28px] border border-[var(--app-border)] bg-white shadow-[0_18px_55px_rgba(15,23,42,.05)]"><div className="flex flex-wrap items-center justify-between gap-4 px-5 py-5 sm:px-7"><div className="flex min-w-0 items-center gap-4"><span className="company-monogram grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-[var(--app-border)] bg-[#fafafa] text-sm font-black shadow-sm"><CompanyLogo ticker={ticker} /></span><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-semibold tracking-[-.045em]">{data.issuer.name}</h1><span className="company-status rounded-full bg-[#fff6df] px-2.5 py-1 text-[9px] font-bold uppercase tracking-[.09em] text-[#8a5c08]">{marketRelative ? 'Market-relative estimate' : 'Provisional intrinsic'}</span></div><p className="mt-1 text-sm text-[var(--app-muted)]">PH · {ticker} · {data.subsector}</p><div className="mt-3 inline-flex rounded-xl border border-[var(--app-border)] bg-[#fbfbfc] p-1 text-[10px] font-bold"><Link to="/valuation/AAPL" className="rounded-lg px-3 py-1.5 text-[var(--app-muted)] hover:text-[var(--app-text)]">US</Link><span className="rounded-lg bg-[#111318] px-3 py-1.5 text-white">PH</span></div></div></div><button type="button" onClick={addToPortfolio} disabled={held || adding} className={cn('portfolio-action inline-flex h-11 items-center gap-2 rounded-xl border px-4 text-sm font-semibold shadow-sm', held ? 'border-[#cfe9da] bg-[#eef8f2] text-[#16794b]' : 'border-[var(--app-border)] bg-white hover:-translate-y-0.5')}><Heart className="h-4 w-4" />{held ? 'In portfolio' : adding ? 'Adding…' : 'Add to portfolio'}</button></div></section>

    <ValuationSwipeDeck key={ticker} date={data.valuation_date} ticker={ticker} labels={['Summary', marketRelative ? 'Relative model' : 'Primary model', 'Cross-checks', 'Key assumptions', 'Source filing']}>
      <div className="valuation-overview"><article className="intrinsic-hero rounded-[26px] border border-[var(--app-border)] bg-white p-6 shadow-[0_16px_45px_rgba(15,23,42,.05)] sm:p-7"><div className="flex items-center gap-2 text-sm font-semibold">{marketRelative ? 'Market-relative value' : 'Intrinsic value'} ({caseLabel}) <Info className="h-4 w-4 text-[var(--app-muted)]" /></div><strong className="value-reveal mt-7 block text-5xl font-semibold tracking-[-.055em] tabular-nums sm:text-6xl">{peso(selectedValue)}</strong>{comparison ? <div className={cn('comparison-badge mt-5 inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold', comparison.verdict === 'overvalued' ? 'bg-[#fff0f2] text-[#d12e4f]' : comparison.verdict === 'undervalued' ? 'bg-[#edf9f2] text-[#168353]' : 'bg-[#f1f2f4]')}>{comparison.verdict === 'overvalued' ? <ArrowDown className="h-4 w-4" /> : <ArrowUp className="h-4 w-4" />}{comparison.label}</div> : <p className="mt-5 text-sm text-[var(--app-muted)]">Enter a market price below to compare it with this value.</p>}<p className="mt-7 text-sm leading-7 text-[var(--app-muted)]">{dirty ? 'Your edited' : 'FinSight’s'} {caseLabel.toLowerCase()} for {data.issuer.name} is {peso(selectedValue)} per share. {marketRelative ? 'This is a screening estimate, not the unavailable specialist intrinsic value.' : 'This is a filing-based educational estimate, not a recommendation.'}</p><div className="overview-context"><div><span>{marketRelative ? 'Low–high range' : 'Bear–bull range'}</span><strong>{peso(range.low)} – {peso(range.high)}</strong></div><div><span>Financial period</span><strong>{data.filing_period ?? 'Source review'}</strong></div><div><span>Evidence documents</span><strong>{data.sources.length}</strong></div></div></article><article className="rounded-[26px] border border-[var(--app-border)] bg-white p-6 shadow-[0_16px_45px_rgba(15,23,42,.05)]"><div className="flex items-center justify-between"><p className="text-xs font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">Valuation summary</p><ShieldCheck className="h-5 w-5" /></div><p className="mt-7 text-xs text-[var(--app-muted)]">{marketRelative ? 'Market-relative value' : 'Intrinsic value'} ({caseLabel})</p><strong className="mt-1 block text-3xl font-semibold">{peso(selectedValue)}</strong><div className="mt-8 grid grid-cols-3 gap-3">{(['low', 'base', 'high'] as const).map(key => <button type="button" key={key} onClick={() => selectCase(key)} aria-pressed={scenario === key} className={cn('scenario-button rounded-xl border border-[var(--app-border)] px-3 py-3 text-xs font-semibold', scenario === key && 'border-[#111318] bg-[#111318] text-white shadow-md')}><span>{key === 'low' ? (marketRelative ? 'Low' : 'Bear') : key === 'high' ? (marketRelative ? 'High' : 'Bull') : 'Base'}</span><strong>{peso(range[key])}</strong></button>)}</div><label className="mt-6 block border-t border-[var(--app-border)] pt-5"><span className="text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">Manual market price</span><div className="mt-2 flex items-center rounded-xl border border-[var(--app-border)] bg-[#fafafa] px-3"><span className="text-sm text-[var(--app-muted)]">₱</span><input type="number" min="0.01" step="0.01" value={manualPrice} onChange={event => setManualPrice(event.target.value)} placeholder="User-entered, session only" className="h-11 w-full bg-transparent px-2 text-sm outline-none" /></div></label></article>{assumptionsPanel}<EvidencePanel data={data} /></div>
      <section className="grid gap-5 md:grid-cols-[1.05fr_.95fr]"><ValueMethod data={data} selectedValue={selectedValue} /><EvidencePanel data={data} /></section>
      <section className="grid gap-5 md:grid-cols-2"><ValueMethod data={data} selectedValue={selectedValue} /><Limitations data={data} /></section>
      <section className="grid gap-5 md:grid-cols-[1.05fr_.95fr]">{assumptionsPanel}<article className="rounded-[24px] border border-[var(--app-border)] bg-white p-6"><p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">Governed baseline</p><div className="mt-4 divide-y divide-[var(--app-border)]">{Object.entries(marketRelative ? data.market_relative?.assumptions ?? {} : data.public_assumptions).filter(([, value]) => typeof value === 'number' || typeof value === 'string').slice(0, 10).map(([key, value]) => <div key={key} className="flex justify-between gap-4 py-3 text-xs"><span className="text-[var(--app-muted)]">{humanize(key)}</span><strong>{typeof value === 'number' && Math.abs(value) < 1 ? pct(value) : String(value)}</strong></div>)}</div></article></section>
      <section className="rounded-[24px] border border-[var(--app-border)] bg-white p-6"><p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">Source filing</p><h2 className="mt-2 text-2xl font-semibold">The evidence behind this value.</h2><p className="mt-3 text-sm leading-7 text-[var(--app-muted)]">Source references and specialist-model limitations remain visible alongside the published estimate.</p><ul className="mt-6 grid gap-3 sm:grid-cols-2">{data.sources.map(source => <li key={source.document_id} className="rounded-2xl bg-[#fafafa] p-4 text-xs"><strong className="block">{source.form ?? 'Filing evidence'}{source.source_page ? ` · p. ${source.source_page}` : ''}</strong><span className="mt-1 block text-[var(--app-muted)]">{source.label}</span>{source.url && <a href={source.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 underline">Open source <ExternalLink className="h-3 w-3" /></a>}</li>)}</ul><details className="mt-6 border-t border-[var(--app-border)] pt-4"><summary className="cursor-pointer text-sm font-semibold">Dated valuation history</summary><ul className="mt-3 space-y-2 text-sm">{history?.items.map(item => <li key={item.catalog_version}>{item.catalog_version} · {item.availability_type.replace(/_/g, ' ')} · {peso(item.range.low)} / {peso(item.range.base)} / {peso(item.range.high)}</li>)}</ul></details></section>
    </ValuationSwipeDeck>
    <footer className="rounded-[20px] border border-[var(--app-border)] bg-white px-5 py-4 text-center text-[10px] text-[var(--app-muted)]"><span className="font-semibold text-[var(--app-text)]">FinSight catalog {data.catalog.catalog_version}</span> · Valuation date {data.valuation_date} · {data.catalog.artifact_count} companies</footer>
  </div>
}

function EvidencePanel({ data }: { data: PseValuation }) {
  return <section className="rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,.04)] sm:p-6"><p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">Evidence health</p><h2 className="mt-1 text-lg font-semibold">How dependable is this value?</h2><div className="mt-4 space-y-3"><EvidenceRow label="Publication state" value={humanize(data.publication_state)} /><EvidenceRow label="Source documents" value={String(data.sources.length)} /><EvidenceRow label="Input classification" value={data.market_relative?.source_status ? humanize(data.market_relative.source_status) : 'Reviewed proxy'} /></div><p className="mt-4 text-[10px] leading-relaxed text-[var(--app-muted)]">Evidence labels describe source and model review, not company financial strength.</p></section>
}
function EvidenceRow({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between rounded-2xl border border-[var(--app-border)] bg-[#fbfbfc] px-4 py-3"><span className="text-sm font-semibold">{label}</span><strong className="text-sm">{value}</strong></div> }
function ValueMethod({ data, selectedValue }: { data: PseValuation; selectedValue: number | undefined }) { return <article className="rounded-[24px] border border-[var(--app-border)] bg-white p-6"><p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">{data.market_relative ? 'Relative model' : 'Primary model'}</p><h2 className="mt-2 text-2xl font-semibold">{humanize(data.market_relative?.metric ?? data.primary_model)}</h2><strong className="mt-6 block text-4xl">{peso(selectedValue)}</strong><p className="mt-4 text-sm leading-7 text-[var(--app-muted)]">{data.market_relative ? `${data.market_relative.metric_label}. ${data.market_relative.note}` : String(data.public_assumptions.route_reason ?? 'Governed FCFF valuation.')}</p></article> }
function Limitations({ data }: { data: PseValuation }) { return <article className="rounded-[24px] border border-[var(--app-border)] bg-white p-6"><p className="text-[10px] font-bold uppercase tracking-[.14em] text-[var(--app-muted)]">Warnings and limitations</p><ul className="mt-4 space-y-3 text-sm leading-6 text-[var(--app-muted)]">{[...data.warnings, ...data.blocking_reasons].map(reason => <li key={reason}>• {reason}</li>)}</ul></article> }
