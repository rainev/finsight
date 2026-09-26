import { ArrowRight, Check, FileText, Layers3, Search, ShieldCheck, SlidersHorizontal, Sparkles, Bookmark, ExternalLink } from 'lucide-react'
import { memo } from 'react'
import { CompanyLogo } from '@/components/CompanyLogo'
import { appleNewsPreview } from '@/lib/valuationNewsPreview'
import snapshot from './snapshot.json'
import type { WalkthroughState } from './timeline'

export type WalkthroughSnapshot = typeof snapshot
export const demo: WalkthroughSnapshot = snapshot
export const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
const percent = (value: number) => `${(value * 100).toFixed(2)}%`
const scenarioKeys = ['low', 'base', 'high'] as const
const scenarioNames = ['Bear', 'Base', 'Bull']

export function StaticAppendix({ index }: { index: number }) {
  if (index === 3) return <p className="wt-static-note">Confirmed default: {percent(demo.assumptions.initial_growth)} → {money(demo.scenarios.base)}. At 12.00% growth: {money(demo.calculatorSamples.at(-1)!.values.base)}. All other governed inputs remain at their confirmed defaults.</p>
  if (index !== 4) return null
  return <div className="wt-static-news">{[14,13,12,11,10,9,8].map(day => {
    const date = `2026-08-${String(day).padStart(2,'0')}`
    const news = appleNewsPreview[date]
    return <details key={day}><summary>August {day}, 2026 · {news?.title || 'No sourced preview'}</summary><p>{news?.summary || 'No sourced news preview is available. This does not mean no news occurred.'}</p>{news && <a href={news.url} target="_blank" rel="noreferrer">Read story ↗</a>}</details>
  })}</div>
}

function Identity({ compact = false }: { compact?: boolean }) {
  return <div className={`wt-identity ${compact ? 'wt-identity-compact' : ''}`}>
    <div className="wt-apple"><CompanyLogo ticker="AAPL" size={38} /></div>
    <div><strong>{demo.company.name}</strong><span>US · AAPL · {demo.company.sector}</span></div>
    {!compact && <span className="wt-reviewed"><Check size={12} /> Reviewed baseline</span>}
  </div>
}

function Range({ selected = 1 }: { selected?: number }) {
  const values = scenarioKeys.map(key => demo.scenarios[key])
  const position = (values[selected] - values[0]) / (values[2] - values[0]) * 100
  return <div className="wt-scenario" data-scenario={scenarioNames[selected].toLowerCase()}>
    <div className="wt-value-label">Intrinsic value · {scenarioNames[selected]} case</div>
    <strong className="wt-value">{money(values[selected])}</strong>
    <div className="wt-range-title"><span>Scenario range</span><span>USD / share</span></div>
    <div className="wt-gauge"><div className="wt-gauge-marker" style={{ left: `${position}%` }} /></div>
    <div className="wt-range-labels"><span>Bear estimate</span><span>Bull estimate</span></div>
    <div className="wt-case-grid">{scenarioNames.map((name, i) => <div key={name} className={`wt-case ${selected === i ? 'is-selected' : ''}`}><span>{name} case</span><strong>{money(values[i])}</strong></div>)}</div>
    <p className="wt-fine">Filing-based educational estimates. No market price supplied.</p>
  </div>
}

function Slider({ name, value, min, max }: { name: string; value: number; min: number; max: number }) {
  const position = (value - min) / (max - min) * 100
  return <div className="wt-assumption">
    <div><span>{name}</span><output>{percent(value)}</output></div>
    <div className="wt-slider" role="meter" aria-label={`${name} demonstration`} aria-valuemin={min * 100} aria-valuemax={max * 100} aria-valuenow={value * 100} aria-valuetext={percent(value)}>
      <span style={{ width: `${position}%` }} /><i style={{ left: `${position}%` }} />
    </div>
    <div className="wt-slider-limits"><span>{percent(min)}</span><span>{percent(max)}</span></div>
  </div>
}

function Evidence() {
  return <div className="wt-evidence">
    <a className="wt-source" href={demo.filing.url} target="_blank" rel="noreferrer"><FileText size={25} /><div><span>Source filing · {demo.filing.form}</span><strong>Apple Inc. / SEC</strong><small>Filed {demo.filing.filed_date}</small></div><ExternalLink size={15} /></a>
    <div className="wt-connectors" aria-hidden="true"><i /><i /><i /></div>
    <div className="wt-evidence-grid">
      <div><span>Reporting period</span><strong>{demo.filing.period_end}</strong></div>
      <div><span>Primary model</span><strong>FCFF · DCF</strong></div>
      <div><span>Bear → Bull</span><strong>{money(demo.scenarios.low)}—{money(demo.scenarios.high)}</strong></div>
      <div><span>Assumptions</span><strong>Governed inputs</strong></div>
    </div>
    <div className="wt-confidence"><ShieldCheck size={18} /><span>Source confidence <b>{demo.reliability.source_cap}</b></span><span>Accounting <b>{demo.reliability.accounting_label}</b></span></div>
    <div className="wt-qualification"><strong>Overall reliability: {demo.reliability.label} · Review required</strong><p>Consolidated-model and specialist-model uncertainty; R&D-life sensitivity. Evidence confidence is not a measure of operating health.</p></div>
  </div>
}

export const Preview = memo(function Preview({ state }: { state: WalkthroughState }) {
  const { index, scenario, calculatorSample, day, added } = state
  const sample = demo.calculatorSamples[calculatorSample]
  const date = `2026-08-${String(14 - day).padStart(2, '0')}`
  const story = appleNewsPreview[date]
  return <div className={`wt-window wt-window-${index}`} data-chapter={index}>
    <div className="wt-window-chrome"><div className="wt-window-brand"><span>F</span> FinSight</div><span className="wt-window-status">Product walkthrough <span aria-hidden="true">↗</span></span></div>
    <div className="wt-window-body">
      {index === 0 && <><Identity /><Range /><div className="wt-mini-strip"><span><Layers3 size={15} /> Filing-based</span><span><SlidersHorizontal size={15} /> Your assumptions</span></div></>}
      {index === 1 && <div className="wt-discovery">
        <div className="wt-search" aria-label={`Search demonstration: ${state.query || 'empty'}`}><Search size={19} /><span>{state.query || 'Search company or ticker'}</span><kbd>⌘ K</kbd></div>
        <div className="wt-discovery-result"><Identity /><div className="wt-demo-action"><Bookmark size={15} /> Add to Portfolio <span>Demo</span></div></div>
        <div className="wt-discovery-detail"><span>One company. The full context.</span><div><span>Valuation</span><span>News</span><span>Source filing</span></div></div>
        <p className="wt-fine">Confirmed Batches 01–10 · Baseline dated August 14, 2026.<br />Reviewed baseline does not remove the Low reliability / review-required qualification.</p>
      </div>}
      {index === 2 && <><Identity compact /><Range selected={scenario} /></>}
      {index === 3 && <><div className="wt-panel-heading"><SlidersHorizontal size={18} /><strong>Key assumptions</strong><span>Scroll demo</span></div><div className="wt-calculation"><span>Illustrative base-case sensitivity</span><strong>{money(sample.values.base)}</strong><small>Default {money(demo.scenarios.base)}</small></div>{demo.assumptionFields.filter(field => ['initial_growth','discount_rate','terminal_growth'].includes(field.key)).map(field => <Slider key={field.key} name={field.label} value={field.key === 'initial_growth' ? sample.growth : demo.assumptions[field.key as 'discount_rate' | 'terminal_growth']} min={field.min} max={field.max} />)}<p className="wt-fine">{demo.calculatorDescription}</p></>}
      {index === 4 && <><div className="wt-panel-heading"><FileText size={18} /><strong>News on this day</strong><span>Curated preview</span></div><div className="wt-news-date">August {14 - day}, 2026</div><div className="wt-days" aria-label="Seven-day news demonstration">{[14, 13, 12, 11, 10, 9, 8].map((d, i) => <div key={d} className={i === day ? 'is-selected' : ''}><span>{['FRI', 'THU', 'WED', 'TUE', 'MON', 'SUN', 'SAT'][i]}</span><strong>{d}</strong><i aria-hidden="true">{i === day ? '—' : '·'}</i></div>)}</div><article className="wt-news-story" data-news-date={date}><div className="wt-story-meta">AAPL <span> / </span> {story ? 'MacRumors' : 'No sourced preview'}</div><h3>{story?.title || 'A quiet page in the journal.'}</h3><p>{story?.summary || 'No sourced news preview is available for this date. That does not mean no news occurred.'}</p>{story && <a href={story.url} target="_blank" rel="noreferrer">Read story <ArrowRight size={16} /></a>}</article><p className="wt-fine">News dates are publication dates, not additional valuation snapshots.</p></>}
      {index === 5 && <><div className="wt-panel-heading"><Layers3 size={18} /><strong>Behind the estimate</strong><span>AAPL</span></div><Evidence /></>}
      {index === 6 && <><div className="wt-panel-heading"><Bookmark size={18} /><strong>Your research, together</strong><span>Demonstration</span></div><div className="wt-watchlist"><span className="wt-eyebrow">WATCHLIST</span><Identity compact /><div className={`wt-demo-action ${added ? 'is-added' : ''}`}>{added ? <Check size={16} /> : <Bookmark size={16} />}{added ? 'Apple added to watchlist' : 'Add Apple to watchlist'}</div></div><div className={`wt-saved ${added ? 'is-added' : ''}`}><div><FileText size={20} /><span>Saved valuation <small>August 14, 2026 · Base case</small></span><strong>{money(demo.scenarios.base)}</strong></div><span className="wt-demo-open">Open saved valuation <ArrowRight size={16} /></span></div><p className="wt-fine">An illustrated account experience. Nothing is added or saved to your actual portfolio.</p></>}
      {index === 7 && <div className="wt-ai"><span className="wt-coming">Coming soon</span><div className="wt-ai-icon"><Sparkles size={30} strokeWidth={1.2} /></div><h3>Context, connected.</h3><p>Filing and news changes, connected to the companies you follow.</p><div className="wt-ai-chain"><span>Followed companies</span><span>Source filings</span><span>Company news</span></div><p className="wt-fine">Portfolio-aware AI Insights is an upcoming feature. No buy, sell, or hold recommendations.</p></div>}
      {index === 8 && <><Identity /><div className="wt-final-tabs"><b>Summary</b><span>Valuation</span><span>News</span><span>Portfolio</span></div><div className="wt-final-grid"><div><span>Intrinsic value · Base</span><strong>{money(demo.scenarios.base)}</strong><small>Filing-based estimate</small></div><div><span>Scenario range</span><strong>{money(demo.scenarios.low)}<i> to </i>{money(demo.scenarios.high)}</strong><small>Bear → Bull</small></div><div><SlidersHorizontal size={17} /><span>Transparent assumptions</span><small>Initial growth {percent(demo.assumptions.initial_growth)}</small></div><div><ShieldCheck size={17} /><span>Evidence, in view</span><small>Low reliability · Review required</small></div></div><div className="wt-final-bottom"><span>Valuation</span><span>News</span><span>Portfolio</span><span>AI Insights</span></div></>}
    </div>
    <div className="wt-window-footer"><span>AAPL · August 14, 2026</span><span>Educational estimate</span></div>
  </div>
})
