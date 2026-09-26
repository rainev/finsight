import { useCallback, useEffect, useState } from 'react'
import { ArrowUpRight, Newspaper, RefreshCw } from 'lucide-react'
import { listNews, refreshNews } from '../lib/api'
import type { NewsArticle } from '../lib/types'
import { useAuth } from '../context/AuthContext'
import { cn } from '@/lib/utils'

function outlet(article: NewsArticle): string {
  try {
    return new URL(article.url).hostname.replace(/^www\./, '')
  } catch {
    return article.source
  }
}

export default function News() {
  const { user } = useAuth()
  const [rows, setRows] = useState<NewsArticle[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(() => listNews().then(setRows).catch((caught) => {
    setError(caught instanceof Error ? caught.message : 'Failed to load news')
  }), [])

  useEffect(() => { load().finally(() => setLoading(false)) }, [load])

  async function refresh() {
    setRefreshing(true)
    setError(null)
    try {
      await refreshNews()
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Refresh failed')
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <section>
      <header className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[var(--app-muted)]">Market news</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-.05em] sm:text-5xl">The latest, without the noise.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--app-muted)]">Sourced headlines shown as published. News never changes FinSight’s intrinsic value unless the filing-based valuation itself is reviewed and updated.</p>
        </div>
        {user?.role === 'admin' && (
          <button type="button" onClick={refresh} disabled={refreshing} className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-[var(--app-border)] bg-white px-4 text-sm font-semibold shadow-sm hover:-translate-y-0.5 disabled:opacity-60">
            <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} /> {refreshing ? 'Refreshing…' : 'Refresh feed'}
          </button>
        )}
      </header>

      <div className="mt-8 flex flex-wrap items-center gap-2 border-b border-[var(--app-border)] pb-4">
        <span className="rounded-xl bg-[#111318] px-4 py-2 text-xs font-semibold text-white">All news</span>
        <span className="rounded-xl px-4 py-2 text-xs font-semibold text-[var(--app-muted)]">Portfolio news</span>
        <span className="ml-auto text-[10px] font-bold uppercase tracking-[.12em] text-[var(--app-muted)]">Source-linked · No recommendations</span>
      </div>

      {error && <p className="mt-5 rounded-2xl border border-[#f2c9cf] bg-[#fff7f8] px-4 py-3 text-sm text-[#a02f43]">{error}</p>}

      {loading ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{[1, 2, 3, 4, 5, 6].map((item) => <div key={item} className="h-60 animate-pulse rounded-[24px] bg-white" />)}</div>
      ) : rows.length === 0 ? (
        <div className="mt-6 rounded-[28px] border border-dashed border-[var(--app-border)] bg-white px-6 py-20 text-center">
          <Newspaper className="mx-auto h-9 w-9 text-[var(--app-muted)]" />
          <h2 className="mt-5 text-2xl font-semibold tracking-[-.035em]">No headlines are available yet.</h2>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-[var(--app-muted)]">The feed will populate when a news source is configured. The rest of the application remains usable without it.</p>
        </div>
      ) : (
        <div className="mt-6 grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((article) => (
            <a key={article.id} href={article.url} target="_blank" rel="noopener noreferrer" className="group flex min-h-64 flex-col rounded-[24px] border border-[var(--app-border)] bg-white p-5 shadow-[0_12px_34px_rgba(15,23,42,.04)] transition hover:-translate-y-1 hover:shadow-[0_18px_46px_rgba(15,23,42,.09)]">
              <div className="flex items-center justify-between gap-3 text-[10px] font-bold uppercase tracking-[.1em] text-[var(--app-muted)]">
                <span className="truncate">{outlet(article)}</span>
                <span className="shrink-0">{article.published_at ? new Date(article.published_at).toLocaleDateString() : 'Recent'}</span>
              </div>
              <h2 className="mt-5 text-lg font-semibold leading-snug tracking-[-.025em]">{article.title}</h2>
              {article.snippet && <p className="mt-3 line-clamp-4 text-sm leading-6 text-[var(--app-muted)]">{article.snippet}</p>}
              <div className="mt-auto flex items-center justify-between border-t border-[var(--app-border)] pt-4 text-xs font-semibold">
                Read source <ArrowUpRight className="h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </div>
            </a>
          ))}
        </div>
      )}
    </section>
  )
}
