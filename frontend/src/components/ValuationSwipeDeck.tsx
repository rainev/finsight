import { Children, useEffect, useRef, useState } from 'react'
import type { ReactNode, PointerEvent } from 'react'
import { ArrowUpRight, Check, ChevronLeft, ChevronRight, MoveHorizontal, Newspaper } from 'lucide-react'
import { appleNewsPreview } from '@/lib/valuationNewsPreview'
import './valuation-swipe.css'

const controls = 'input, select, textarea, button, a, label, [role="slider"], [contenteditable="true"]'
const NEWS_DAYS = 7

export function ValuationSwipeDeck({ labels, date, ticker, children }: {
  labels: string[]
  date: string
  ticker: string
  children: ReactNode
}) {
  const [index, setIndex] = useState(0)
  const [dayIndex, setDayIndex] = useState(0)
  const [viewedDays, setViewedDays] = useState<Set<number>>(() => new Set([0]))
  const [offset, setOffset] = useState(0)
  const [dragging, setDragging] = useState(false)
  const tabBar = useRef<HTMLDivElement>(null)
  const sectionAnchor = useRef<HTMLDivElement>(null)
  const gesture = useRef<{ id: number; x: number; y: number; axis: 'x' | 'y' | null; dx: number } | null>(null)
  const pages = Children.toArray(children)
  const last = pages.length - 1
  const dates = Array.from({ length: NEWS_DAYS }, (_, i) => {
    const day = new Date(`${date}T12:00:00Z`)
    if (Number.isNaN(day.getTime())) return date
    day.setUTCDate(day.getUTCDate() - i)
    return day.toISOString().slice(0, 10)
  })
  function goDay(next: number) {
    const bounded = Math.max(0, Math.min(NEWS_DAYS - 1, next))
    setDayIndex(bounded)
    setViewedDays(current => new Set([...current, bounded]))
    setOffset(0)
    setDragging(false)
  }
  useEffect(() => {
    const bar = tabBar.current
    const selected = bar?.children[index] as HTMLElement | undefined
    if (!bar || !selected) return
    bar.scrollTo({ left: selected.offsetLeft - bar.offsetLeft - (bar.clientWidth - selected.offsetWidth) / 2, behavior: 'auto' })
  }, [index])
  function go(next: number) {
    setIndex(Math.max(0, Math.min(last, next)))
    setOffset(0)
    setDragging(false)
    requestAnimationFrame(() => sectionAnchor.current?.scrollIntoView({ block: 'start', behavior: 'auto' }))
  }
  function start(event: PointerEvent<HTMLDivElement>) {
    if (!event.isPrimary || event.button !== 0 || (event.target as Element).closest(controls)) return
    gesture.current = { id: event.pointerId, x: event.clientX, y: event.clientY, axis: null, dx: 0 }
  }
  function move(event: PointerEvent<HTMLDivElement>) {
    const g = gesture.current
    if (!g || g.id !== event.pointerId) return
    const dx = event.clientX - g.x
    const dy = event.clientY - g.y
    if (!g.axis && Math.max(Math.abs(dx), Math.abs(dy)) > 10) {
      g.axis = Math.abs(dx) > Math.abs(dy) * 1.3 ? 'x' : 'y'
      if (g.axis === 'x') event.currentTarget.setPointerCapture(event.pointerId)
    }
    if (g.axis !== 'x') return
    g.dx = dx
    setDragging(true)
    setOffset((dayIndex === 0 && dx > 0) || (dayIndex === NEWS_DAYS - 1 && dx < 0) ? dx * 0.22 : dx)
  }
  function finish(event: PointerEvent<HTMLDivElement>, cancelled = false) {
    const g = gesture.current
    if (!g || g.id !== event.pointerId) return
    gesture.current = null
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    const threshold = Math.min(80, event.currentTarget.clientWidth * 0.16)
    goDay(!cancelled && g.axis === 'x' && Math.abs(g.dx) > threshold ? dayIndex + (g.dx < 0 ? 1 : -1) : dayIndex)
  }
  const formatDate = (value: string) => {
    const parsed = new Date(`${value}T12:00:00Z`)
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
  }
  return (
    <section className="valuation-deck" aria-label="Valuation workspace">
      <div className={`valuation-news-browser${dragging ? ' is-dragging' : ''}`} role="region" aria-label="Daily company news" tabIndex={0} onKeyDown={event => {
        if ((event.target as Element).closest(controls)) return
        if (event.key === 'ArrowLeft') { event.preventDefault(); goDay(dayIndex - 1) }
        if (event.key === 'ArrowRight') { event.preventDefault(); goDay(dayIndex + 1) }
      }} onPointerDown={start} onPointerMove={move} onPointerUp={finish} onPointerCancel={event => finish(event, true)} onLostPointerCapture={event => finish(event, true)}>
      <header className="valuation-deck-header">
        <div className="valuation-deck-date"><span>News on this day</span><time aria-live="polite" dateTime={dates[dayIndex]}>{formatDate(dates[dayIndex])}</time></div>
        <div className="valuation-deck-pager">
          <button type="button" onClick={() => goDay(dayIndex - 1)} disabled={dayIndex === 0} aria-label="Later news day"><ChevronLeft size={18} /></button>
          <div className="valuation-deck-dots" aria-label="News dates">
            {dates.map((day, i) => <button type="button" key={day} onClick={() => goDay(i)} aria-label={`News for ${formatDate(day)}`} aria-current={i === dayIndex ? 'date' : undefined}><span className={i === dayIndex ? 'active' : ''} /></button>)}
          </div>
          <button type="button" onClick={() => goDay(dayIndex + 1)} disabled={dayIndex === NEWS_DAYS - 1} aria-label="Earlier news day"><ChevronRight size={18} /></button>
        </div>
      </header>
      <div className="brief-calendar" aria-label="Browse seven news days, newest first">
        {dates.map((day, dayPosition) => {
          const parsed = new Date(`${day}T12:00:00Z`)
          return <button type="button" key={day} className={dayPosition === dayIndex ? 'selected' : ''} aria-pressed={dayPosition === dayIndex} aria-label={`Browse news for ${formatDate(day)}`} onClick={() => goDay(dayPosition)}>
            <span>{parsed.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' })}</span>
            <strong>{Number(day.slice(-2))}</strong>
            <span className="calendar-visited" aria-label={viewedDays.has(dayPosition) ? 'Viewed this visit' : 'Not viewed this visit'}>{viewedDays.has(dayPosition) ? <Check size={10} /> : <span className="calendar-dot" />}</span>
          </button>
        })}
      </div>
      <div className="valuation-news-viewport">
        <div className="valuation-news-track" style={{ transform: `translateX(calc(${-dayIndex * 100}% + ${offset}px))` }}>
          {dates.map((day, i) => {
            const story = ticker === 'AAPL' ? appleNewsPreview[day] : undefined
            return <div key={day} className="valuation-news-slide" aria-hidden={i !== dayIndex} ref={node => { if (node) { if (i !== dayIndex) node.setAttribute('inert', ''); else node.removeAttribute('inert') } }}>
              <article className="valuation-news-card">
                <span className="valuation-news-icon" aria-hidden="true"><Newspaper size={23} /><small>BRIEF</small></span>
                <div className="valuation-news-copy">
                  <div className="valuation-news-meta"><span>{ticker} · Daily brief</span><span className="valuation-news-preview">{story ? 'Curated preview' : 'Preview'}</span></div>
                  <h2>{story?.title ?? 'News preview coming soon'}</h2>
                  <p>{story?.summary ?? `A short ${ticker} news summary for this date will appear here when the feed is connected.`}</p>
                  {story && <a href={story.url} target="_blank" rel="noreferrer">Read story <ArrowUpRight size={14} /><span>MacRumors · {formatDate(day)}</span></a>}
                </div>
              </article>
            </div>
          })}
        </div>
      </div>
      <div className="valuation-news-hint">
        {dayIndex > 0 ? <button type="button" className="brief-latest" onClick={() => goDay(0)}><ChevronLeft size={13} /> Back to latest</button> : <span><MoveHorizontal size={14} /> Latest first · swipe left for earlier days</span>}
        <span className="brief-viewed" aria-live="polite">{viewedDays.size === NEWS_DAYS ? <Check size={13} /> : null}{viewedDays.size} of {NEWS_DAYS} dates explored</span>
      </div>
      <div className="brief-progress" aria-hidden="true"><span style={{width:`${viewedDays.size / NEWS_DAYS * 100}%`}} /></div>
      </div>
      <div ref={sectionAnchor} className="valuation-section-anchor" />
      <div ref={tabBar} className="valuation-deck-tabs" role="tablist" aria-label="Valuation sections">
        {labels.map((label, i) => <button id={`valuation-tab-${i}`} type="button" role="tab" aria-selected={i === index} aria-controls={`valuation-panel-${i}`} tabIndex={i === index ? 0 : -1} key={label} onClick={() => go(i)} onKeyDown={event => {
          const target = event.key === 'ArrowRight' ? Math.min(last, i + 1) : event.key === 'ArrowLeft' ? Math.max(0, i - 1) : event.key === 'Home' ? 0 : event.key === 'End' ? last : null
          if (target === null) return
          event.preventDefault(); go(target); document.getElementById(`valuation-tab-${target}`)?.focus()
        }}><span className="valuation-section-number">0{i + 1}</span>{label}</button>)}
      </div>
      <div className="valuation-deck-content">
          {pages.map((page, i) => <div key={i} id={`valuation-panel-${i}`} role="tabpanel" aria-labelledby={`valuation-tab-${i}`} hidden={i !== index} className="valuation-deck-page" tabIndex={i === index ? 0 : -1}>{page}</div>)}
      </div>
      <footer className="valuation-deck-foot"><span aria-live="polite"><strong>{labels[index]}</strong> · {index + 1} of {pages.length}</span><span>Valuation as of {formatDate(date)}</span></footer>
    </section>
  )
}
