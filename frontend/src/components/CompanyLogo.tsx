/** Shared, presentation-only identity; never fetches or changes account state. */
export function CompanyLogo({ ticker, size = 34 }: { ticker: string; size?: number }) {
  return ticker === 'AAPL'
    ? <img src="/logos/apple.svg" alt="Apple logo" width={size} height={size} />
    : <span aria-label={`${ticker} logo`}>{ticker.slice(0, 3)}</span>
}
