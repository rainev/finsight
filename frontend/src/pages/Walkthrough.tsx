import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { ArrowDown, ArrowRight, MoveUpRight } from 'lucide-react'
import { Preview, StaticAppendix, demo } from '@/walkthrough/Preview'
import { chapters, chapterStart, sampleTimeline, totalWeight } from '@/walkthrough/timeline'
import type { createScene } from '@/walkthrough/scene'
import '@/walkthrough/walkthrough.css'

const copy = [
  { eyebrow: 'A clearer perspective', title: 'Know what a company is actually worth.', text: 'Filing-based valuations, transparent assumptions, and relevant company news.', note: 'Explore the thinking behind the number.' },
  { eyebrow: '01 / Discover', title: 'Start with a company. See the bigger picture.', text: 'From a ticker to its valuation, assumptions, and source filing. One connected place to begin your research.', note: 'A familiar name. A more informed perspective.' },
  { eyebrow: '02 / Valuation', title: 'One business. More than one possibility.', text: 'Explore bear, base, and bull cases side by side. Understand the range—not just a single headline number.', note: 'An estimate, not a price target or recommendation.' },
  { eyebrow: '03 / Assumptions', title: 'The inputs matter. Make them visible.', text: 'Follow initial growth from its confirmed default to 12%. Watch the existing calculator’s sensitivity samples update the estimate.', note: 'Transparent assumptions. Clearly stated limits.' },
  { eyebrow: '04 / Company news', title: 'Every company has a story. Follow the dates.', text: 'Move back through a week of sourced company news. Keep the reporting separate from the valuation—and see both in context.', note: 'August 14–8, 2026 · Newest first' },
  { eyebrow: '05 / Evidence', title: 'See what supports every estimate.', text: 'Trace the number to the source filing, reporting period, model, and governed assumptions. The qualifications stay in view, too.', note: 'Source confidence is not investment certainty.' },
  { eyebrow: '06 / Portfolio', title: 'Less searching. More connecting.', text: 'Keep followed companies and saved valuations close. Return to your research without starting from scratch.', note: 'Watchlist demonstration · No account changes' },
  { eyebrow: '07 / AI Insights', title: 'Your research. With more context.', text: 'Coming soon: portfolio-aware insights connecting sourced filing and news changes to the companies you follow.', note: 'A forthcoming feature, not an investment adviser.' },
  { eyebrow: 'Your next perspective', title: 'Research with context. Value with clarity.', text: 'The walkthrough ends here. Your research starts with FinSight.', note: 'Filing-based educational estimates. Not investment advice.' },
]
const staticStates = chapters.map((chapter, index) => sampleTimeline(chapterStart(index) + chapter.weight * (index === 4 ? 0.01 : 0.999) / totalWeight))

export default function Walkthrough() {
  const root = useRef<HTMLElement>(null)
  const story = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const [reduced, setReduced] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [compact, setCompact] = useState(() => window.matchMedia('(max-height: 700px)').matches)
  const [simple, setSimple] = useState(() => new URLSearchParams(window.location.search).get('view') === 'static')
  const [attempt, setAttempt] = useState(0)
  const [mode, setMode] = useState<'loading' | 'cinematic' | 'static'>(reduced || simple || compact ? 'static' : 'loading')
  const [state, setState] = useState(() => sampleTimeline(0))

  useEffect(() => {
    const previousTitle = document.title
    document.title = 'FinSight — A clearer perspective'
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const heightQuery = window.matchMedia('(max-height: 700px)')
    const changed = () => setReduced(query.matches)
    const heightChanged = () => setCompact(heightQuery.matches)
    query.addEventListener('change', changed)
    heightQuery.addEventListener('change', heightChanged)
    return () => { document.title = previousTitle; query.removeEventListener('change', changed); heightQuery.removeEventListener('change', heightChanged) }
  }, [])

  useEffect(() => {
    if (simple || reduced || compact) { setMode('static'); return }
    setMode('loading')
    let scene: ReturnType<typeof createScene> | undefined
    let disposed = false
    let failed = false
    let frame = 0
    const fail = () => {
      if (disposed || failed) return
      failed = true
      scene?.dispose()
      scene = undefined
      setMode('static')
    }
    const draw = () => {
      frame = 0
      if (disposed || failed || document.hidden || !story.current) return
      const first = story.current.querySelector<HTMLElement>('.wt-chapter')
      if (!first) return
      const header = window.innerWidth <= 760 ? 68 : 80
      const progress = (header - story.current.getBoundingClientRect().top + 0.5) / (first.getBoundingClientRect().height * totalWeight)
      const next = sampleTimeline(progress, demo.calculatorSamples.length)
      const mobile = window.innerWidth <= 760
      const restraint = mobile ? 0.35 : 1
      if (panel.current) {
        panel.current.style.transform = `perspective(1400px) translate3d(${next.x * restraint}px, ${next.y * restraint}px, 0) rotateX(${next.pitch * restraint}deg) rotateY(${next.yaw * restraint}deg) rotateZ(${next.roll * restraint}deg) scale(${next.scale})`
        // Continuous component choreography lives in compositor-friendly CSS
        // variables, so exact financial samples need no invented in-between values.
        const style = panel.current.style
        const strength = mobile ? 0.28 : 1
        style.setProperty('--wt-piece-x', `${(1 - next.reveal) * 68 * strength}px`)
        style.setProperty('--wt-piece-y', `${(1 - next.reveal) * 46 * strength}px`)
        style.setProperty('--wt-fan-angle', `${(1 - next.reveal) * 9 * strength}deg`)
        style.setProperty('--wt-drift-x', `${(next.local - 0.5) * 36 * strength}px`)
        style.setProperty('--wt-spread', `${next.reveal * 26 * strength}px`)
        style.setProperty('--wt-story-x', `${Math.sin(next.action * 7 * Math.PI) * 18 * strength}px`)
        style.setProperty('--wt-icon-turn', `${(next.local - 0.5) * 36 * strength}deg`)
        for (let i = 0; i < 3; i++) {
          const lift = Math.max(0, 1 - Math.abs(next.action * 3 - 0.5 - i))
          style.setProperty(`--wt-case-${i}-lift`, `${-24 * lift * strength}px`)
        }
        for (let i = 0; i < 7; i++) {
          const lift = Math.max(0, 1 - Math.abs(next.action * 7 - 0.5 - i))
          style.setProperty(`--wt-day-${i}-lift`, `${-12 * lift * strength}px`)
        }
      }
      root.current?.style.setProperty('--wt-progress', String(next.progress))
      root.current?.style.setProperty('--wt-copy-shift', `${(0.5 - next.local) * (mobile ? 8 : 28)}px`)
      if (root.current) root.current.dataset.renderedScroll = String(window.scrollY)
      // Camera changes do not require reconciling all the semantic HTML. Update
      // React only when visible content changes; the sampler remains authoritative.
      setState(previous => previous.index === next.index && previous.scenario === next.scenario && previous.calculatorSample === next.calculatorSample && previous.day === next.day && previous.query === next.query && previous.added === next.added ? previous : next)
      try { scene?.render(next, mobile) } catch { fail() }
    }
    const schedule = () => { if (!frame && !document.hidden && !failed) frame = requestAnimationFrame(draw) }
    const visibility = () => { if (document.hidden) { cancelAnimationFrame(frame); frame = 0 } else schedule() }
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule, { passive: true })
    document.addEventListener('visibilitychange', visibility)
    const resize = new ResizeObserver(schedule)
    if (panel.current) resize.observe(panel.current)
    // Defer the procedural 3D bundle until after the initial semantic HTML paint.
    const loadFrame = requestAnimationFrame(() => {
      import('@/walkthrough/scene').then(module => {
        if (disposed || !canvas.current) return
        try { scene = module.createScene(canvas.current, fail); setMode('cinematic'); schedule() } catch { fail() }
      }).catch(fail)
    })
    schedule()
    return () => {
      disposed = true
      cancelAnimationFrame(frame); cancelAnimationFrame(loadFrame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
      document.removeEventListener('visibilitychange', visibility)
      resize.disconnect()
      scene?.dispose()
    }
  }, [simple, reduced, compact, attempt])

  // Explicit motion toggle restores the current chapter after the layout changes.
  const toggleMotion = () => {
    const id = chapters[state.index].id
    if (mode === 'static') { setSimple(false); setAttempt(value => value + 1) }
    else setSimple(true)
    requestAnimationFrame(() => requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ block: 'start' })))
  }

  return <main ref={root} className="wt" data-mode={mode} data-active-chapter={chapters[state.index].id}>
    <a className="wt-access-skip" href="#continue">Skip to final invitation</a>
    <header className="wt-header">
      <a href="#intro" className="wt-brand" aria-label="FinSight introduction"><span>F</span>FinSight</a>
      <span className="wt-header-caption">A clearer perspective on investing.</span>
      <button className="wt-motion-toggle" type="button" onClick={toggleMotion} disabled={reduced || compact}>{reduced ? 'Reduced motion' : compact ? 'Compact view' : mode === 'static' ? 'Cinematic view' : 'Simple view'}</button>
      <Link className="wt-skip" to="/valuation/AAPL">Skip to FinSight <MoveUpRight size={16} /></Link>
    </header>
    <nav className="wt-chapter-nav" aria-label="Walkthrough chapters">
      {chapters.map((chapter, i) => <a key={chapter.id} href={`#${chapter.id}`} aria-label={`${i + 1}. ${chapter.label}`} aria-current={mode !== 'static' && state.index === i ? 'step' : undefined}><span className="wt-nav-dot" /><span className="wt-nav-label">{chapter.label}</span></a>)}
    </nav>
    <div className="wt-story" ref={story}>
      <div className="wt-chapters">
        {chapters.map((chapter, index) => {
          const content = copy[index]
          const staticState = staticStates[index]
          return <section id={chapter.id} key={chapter.id} className={`wt-chapter wt-chapter-${index} ${state.index === index ? 'is-active' : ''}`} style={{ '--wt-weight': chapter.weight } as CSSProperties} aria-labelledby={`${chapter.id}-title`}>
            <div className="wt-copy">
              <span className="wt-eyebrow">{content.eyebrow}</span>
              {index === 0 ? <h1 id={`${chapter.id}-title`}>{content.title}</h1> : <h2 id={`${chapter.id}-title`}>{content.title}</h2>}
              <p>{content.text}</p>
              {index === 0 && <a className="wt-explore" href="#discover" tabIndex={mode === 'static' || state.index === 0 ? 0 : -1}>Scroll to explore <ArrowDown size={16} /></a>}
              {index === 8 && <Link to="/valuation/AAPL" className="wt-cta" tabIndex={mode === 'static' || state.index === 8 ? 0 : -1}>Continue to FinSight <ArrowRight size={19} /></Link>}
              <small className="wt-copy-note">{content.note}</small>
            </div>
            <div className="wt-static-preview"><Preview state={staticState} /><StaticAppendix index={index} /></div>
          </section>
        })}
      </div>
      <aside className="wt-stage" aria-label="FinSight interface demonstration">
        <canvas ref={canvas} className="wt-canvas" aria-hidden="true" />
        <div className="wt-stage-panel" ref={panel}><Preview state={state} /></div>
        <div className="wt-stage-caption"><span className="wt-stage-line" /><span>Dated product demonstration</span><span>Not a live quote</span></div>
      </aside>
    </div>
    <footer className="wt-footer"><span>FinSight <span> / </span> Clarity begins with context.</span><button type="button" onClick={toggleMotion} disabled={reduced || compact}>{reduced ? 'Reduced-motion view' : compact ? 'Compact view · More room to read' : simple ? 'Enable cinematic view' : mode === 'static' ? 'Static view · 3D unavailable' : 'Use simple view'}</button><small>Demonstration snapshot: August 14, 2026 · Confirmed Batches 01–10</small></footer>
    <div className="wt-progress" aria-hidden="true" />
  </main>
}
