import { ArrowRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function AiInsights() {
  return (
    <section className="mx-auto flex min-h-[68vh] max-w-4xl items-center justify-center">
      <div className="w-full rounded-[30px] border border-[var(--app-border)] bg-white px-6 py-16 text-center shadow-[0_18px_60px_rgba(15,23,42,.06)] sm:px-14">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#111318] text-white shadow-[0_10px_26px_rgba(15,23,42,.18)]">
          <Sparkles className="h-6 w-6" />
        </span>
        <p className="mt-7 text-[10px] font-bold uppercase tracking-[.2em] text-[var(--app-muted)]">Coming soon</p>
        <h1 className="mx-auto mt-3 max-w-2xl text-4xl font-semibold tracking-[-.05em] sm:text-5xl">
          AI insights, grounded in what you follow.
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-sm leading-7 text-[var(--app-muted)]">
          This destination is intentionally a preview for now. Future insights will connect sourced filing and news changes to companies in your portfolio without presenting buy, sell, or hold recommendations.
        </p>
        <Link
          to="/portfolio"
          className="mt-8 inline-flex h-11 items-center gap-2 rounded-xl bg-[#111318] px-5 text-sm font-semibold text-white shadow-sm hover:-translate-y-0.5"
        >
          Build your portfolio <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  )
}
