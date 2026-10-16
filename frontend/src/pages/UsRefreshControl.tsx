import { useCallback, useEffect, useState } from 'react'
import { Clock3, LockKeyhole, Play, RotateCw, ShieldCheck, UserPlus, X } from 'lucide-react'
import { getUsRefreshControl, inviteUsRefreshUser, revokeUsRefreshUser, startUsManualRefresh, startUsStagedRefresh } from '../lib/api'
import type { UsRefreshControlStatus } from '../lib/types'

const dateTime = (value: string) => new Intl.DateTimeFormat('en-PH', {
  timeZone: 'Asia/Manila', dateStyle: 'full', timeStyle: 'short',
}).format(new Date(value))

function remaining(target: string, now: number): string {
  const seconds = Math.max(0, Math.floor((new Date(target).getTime() - now) / 1000))
  if (!seconds) return 'Ready now'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${days}d ${hours}h ${minutes}m`
}

export default function UsRefreshControl() {
  const [data, setData] = useState<UsRefreshControlStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [now, setNow] = useState(Date.now())
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [email, setEmail] = useState('')

  const load = useCallback(async () => {
    try {
      setData(await getUsRefreshControl())
      setError(null)
    } catch (caught) {
      setData(null)
      setError(caught instanceof Error ? caught.message : 'US refresh control is unavailable')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const clock = window.setInterval(() => setNow(Date.now()), 1000)
    const poll = window.setInterval(() => { void load() }, 15000)
    return () => { window.clearInterval(clock); window.clearInterval(poll) }
  }, [load])

  async function run(kind: 'weekly' | 'manual') {
    setBusy(true)
    try {
      if (kind === 'manual') await startUsManualRefresh()
      else await startUsStagedRefresh()
      setConfirming(false)
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not queue the US refresh')
    } finally { setBusy(false) }
  }

  async function invite() {
    setBusy(true)
    try {
      await inviteUsRefreshUser(email.trim())
      setEmail('')
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not invite this account')
    } finally { setBusy(false) }
  }

  async function revoke(userId: number) {
    setBusy(true)
    try {
      await revokeUsRefreshUser(userId)
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not revoke access')
    } finally { setBusy(false) }
  }

  if (loading) return <div className="py-20 text-center text-sm text-[var(--app-muted)]">Checking access…</div>
  if (!data) return <div className="mx-auto mt-16 max-w-lg rounded-3xl border border-[var(--app-border)] bg-white p-10 text-center"><LockKeyhole className="mx-auto h-8 w-8" /><h1 className="mt-4 text-2xl font-semibold">Page unavailable</h1><p className="mt-2 text-sm text-[var(--app-muted)]">This private US control is available only to its owner and separately invited FinSight accounts.</p></div>

  const job = data.latest_job
  const running = data.active_job !== null
  const result = job?.result

  return <section className="mx-auto max-w-5xl pb-12">
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[.18em] text-[var(--app-muted)]">Private operations · US universe</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-[-.05em] sm:text-5xl">Staged refresh</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--app-muted)]">Check every company in the active catalog for new SEC filings and recalculate only source-supported intrinsic values. Unsupported filings are held. This never publishes a new catalog.</p>
      </div>
      <span className="inline-flex items-center gap-2 rounded-full border border-[#cbe9d8] bg-[#edf9f2] px-3 py-1.5 text-xs font-bold text-[#147a49]"><ShieldCheck className="h-4 w-4" /> Invite-only</span>
    </div>

    {error && <div role="alert" className="mt-6 rounded-2xl border border-[#f2c9cf] bg-[#fff7f8] px-4 py-3 text-sm text-[#a02f43]">{error}</div>}

    <div className="mt-8 grid gap-5 lg:grid-cols-[1.15fr_.85fr]">
      <div className="rounded-[28px] border border-[var(--app-border)] bg-white p-6 shadow-[0_14px_45px_rgba(15,23,42,.05)] sm:p-8">
        <div className="flex items-center gap-3 text-xs font-bold uppercase tracking-[.14em] text-[var(--app-muted)]"><Clock3 className="h-4 w-4" /> Friday window · Manila time</div>
        <p className="mt-6 text-4xl font-semibold tracking-[-.055em] sm:text-5xl">{data.ready ? 'Friday slot ready' : remaining(data.next_due_at, now)}</p>
        <p className="mt-3 text-sm text-[var(--app-muted)]">{data.ready ? 'This week’s staged check can be started now.' : `Next available: ${dateTime(data.next_due_at)}`}</p>
        <p className="mt-1 text-xs text-[var(--app-muted)]">The server enforces the weekly limit; this countdown is only a display.</p>
        {confirming ? <div className="mt-8 rounded-2xl border border-[#d9e3ee] bg-[#f6f9fc] p-5">
          <p className="text-sm font-semibold">Run one US staged refresh?</p>
          <p className="mt-2 text-sm text-[var(--app-muted)]">This checks SEC filings and stages supported new values. The active catalog stays unchanged.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" disabled={busy} onClick={() => { void run('weekly') }} className="rounded-xl bg-[#111318] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Queueing…' : 'Confirm and run'}</button>
            <button type="button" disabled={busy} onClick={() => setConfirming(false)} className="rounded-xl border border-[var(--app-border)] bg-white px-4 py-2.5 text-sm font-semibold">Cancel</button>
          </div>
        </div> : <div className="mt-8 flex flex-wrap items-center gap-3">
          <button type="button" disabled={!data.manual_ready || running || busy} onClick={() => { void run('manual') }} className="inline-flex h-12 items-center gap-2 rounded-xl bg-[#111318] px-5 text-sm font-semibold text-white shadow-[0_10px_24px_rgba(15,23,42,.14)] disabled:cursor-not-allowed disabled:opacity-45"><RotateCw className="h-4 w-4" /> Refresh now</button>
          <button type="button" disabled={!data.ready || running || busy} onClick={() => setConfirming(true)} className="inline-flex h-12 items-center gap-2 rounded-xl border border-[var(--app-border)] bg-white px-5 text-sm font-semibold shadow-sm disabled:cursor-not-allowed disabled:opacity-45"><Play className="h-4 w-4" /> Run Friday refresh</button>
        </div>}
        <p className="mt-3 text-xs text-[var(--app-muted)]">Refresh now is independent of the Friday slot and stages only.{!data.manual_ready && data.manual_next_at ? ` Available again ${dateTime(data.manual_next_at)}.` : ''}</p>
      </div>

      <div className="rounded-[28px] border border-[var(--app-border)] bg-white p-6 shadow-[0_14px_45px_rgba(15,23,42,.05)] sm:p-8">
        <div className="flex items-center justify-between"><h2 className="text-xl font-semibold tracking-[-.035em]">Latest run</h2><button type="button" onClick={() => { void load() }} aria-label="Check US refresh status" className="grid h-9 w-9 place-items-center rounded-xl border border-[var(--app-border)]"><RotateCw className="h-4 w-4" /></button></div>
        {!job ? <p className="mt-6 text-sm text-[var(--app-muted)]">No US refresh has been launched from this control yet.</p> : <>
          <p className="mt-5 text-sm"><span className="font-semibold">Status:</span> <span className="capitalize">{job.status}</span> · {job.kind === 'manual' ? 'On-demand' : 'Friday'} check</p>
          <p className="mt-1 text-xs text-[var(--app-muted)]">Requested {dateTime(job.requested_at)}</p>
          {(job.status === 'queued' || job.status === 'running') && <p className="mt-5 text-sm text-[var(--app-muted)]">Checking SEC filing histories for every company in the active catalog. This can take several minutes; you may leave this page.</p>}
          {job.error && <p className="mt-5 rounded-xl bg-[#fff7f8] p-3 text-sm text-[#a02f43]">{job.error}</p>}
          {result && <div className="mt-6 grid grid-cols-3 gap-3 text-center"><div className="rounded-xl bg-[#f3f6f8] p-4"><strong className="block text-2xl">{result.selected_count}</strong><span className="text-xs text-[var(--app-muted)]">Checked</span></div><div className="rounded-xl bg-[#f3f6f8] p-4"><strong className="block text-2xl">{result.staged_intrinsic_count}</strong><span className="text-xs text-[var(--app-muted)]">Staged intrinsic</span></div><div className="rounded-xl bg-[#f3f6f8] p-4"><strong className="block text-2xl">{result.held_count}</strong><span className="text-xs text-[var(--app-muted)]">Held for review</span></div></div>}
          {result?.candidate && <p className="mt-4 break-all text-xs text-[var(--app-muted)]">Staged catalog: {result.candidate.version}</p>}
          {result?.held_tickers_preview.length ? <p className="mt-3 text-xs text-[var(--app-muted)]">Held (first {result.held_tickers_preview.length}): {result.held_tickers_preview.join(', ')}{result.held_count > result.held_tickers_preview.length ? ` and ${result.held_count - result.held_tickers_preview.length} more` : ''}</p> : null}
        </>}
      </div>
    </div>

    {data.owner && <div className="mt-6 rounded-[28px] border border-[var(--app-border)] bg-white p-6 sm:p-8">
      <div className="flex items-center gap-2"><UserPlus className="h-5 w-5" /><h2 className="text-xl font-semibold tracking-[-.035em]">Invited operators</h2></div>
      <p className="mt-2 text-sm text-[var(--app-muted)]">US access is separate from PSE refresh access. Only the owner account can grant or revoke it. This owner login is shared, so actions identify the account, not which person used it. No invitation email is sent.</p>
      <form className="mt-5 flex flex-wrap gap-2" onSubmit={event => { event.preventDefault(); void invite() }}>
        <input type="email" required value={email} onChange={event => setEmail(event.target.value)} placeholder="Their FinSight sign-in email" aria-label="FinSight account email to invite for US refresh" className="h-11 min-w-0 flex-1 rounded-xl border border-[var(--app-border)] px-4 text-sm outline-none" />
        <button type="submit" disabled={busy || !email.trim()} className="h-11 rounded-xl bg-[#111318] px-4 text-sm font-semibold text-white disabled:opacity-50">Grant access</button>
      </form>
      <div className="mt-4 divide-y divide-[var(--app-border)]">
        {(data.invites ?? []).length === 0 ? <p className="py-4 text-sm text-[var(--app-muted)]">No one else has access yet.</p> : data.invites?.map(person => <div key={person.user_id} className="flex items-center justify-between gap-3 py-3"><span className="min-w-0 truncate text-sm font-medium">{person.email}</span><button type="button" disabled={busy} onClick={() => { void revoke(person.user_id) }} aria-label={`Revoke ${person.email}`} className="inline-flex items-center gap-1 rounded-xl px-3 py-2 text-xs font-semibold text-[#a02f43] hover:bg-[#fff7f8] disabled:opacity-50"><X className="h-3 w-3" /> Revoke</button></div>)}
      </div>
    </div>}
    <p className="mt-6 text-xs leading-5 text-[var(--app-muted)]"><LockKeyhole className="mr-1 inline h-3.5 w-3.5" /> Private SEC facts and recipes are not shown here. A completed check never approves or activates a catalog.</p>
  </section>
}
