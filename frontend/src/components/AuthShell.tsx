import type { ReactNode } from 'react'
import { LineChart } from 'lucide-react'

const MODELS = ['Cash flow', 'Residual income', 'Dividend', 'FFO']
const TAPE = 'AAPL  MSFT  JPM  O  AMZN  GOOGL  TSLA  WMT  '

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden border-r border-[var(--app-border)] bg-[#f3f4f6] text-[#111318] lg:flex lg:flex-col lg:justify-between lg:p-12">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#111318] text-white">
            <LineChart className="h-5 w-5" />
          </span>
          <span className="font-display text-lg font-bold tracking-tight">
            FinSight
          </span>
        </div>

        <div className="max-w-md">
          <h2 className="font-display text-4xl font-bold leading-[1.1] tracking-tight">
            Know what a company is <span className="underline decoration-2 underline-offset-4">actually</span> worth.
          </h2>
          <p className="mt-4 text-[#696e78]">
            Explore confirmed, filing-based U.S. valuation baselines with transparent assumptions and source attribution.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {MODELS.map((m) => (
              <span key={m} className="rounded-full border border-[#d8dbe0] bg-white px-3 py-1 text-xs text-[#555b65] shadow-sm">
                {m}
              </span>
            ))}
          </div>
        </div>

        <div className="overflow-hidden">
          <div className="whitespace-nowrap font-mono text-xs tracking-widest text-black/10">{TAPE.repeat(3)}</div>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center bg-white px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <span className="font-display text-2xl font-bold tracking-tight">
              FinSight
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
      </div>
    </div>
  )
}
