// Shared types. The backend is Python/Pydantic, so these are hand-kept in sync
// with app/models/*.py (JSON is snake_case on both sides).

export type Role = 'user' | 'admin'

export interface PublicUser {
  id: number
  email: string
  role: Role
  is_verified: boolean
}

export interface AuthResponse {
  user: PublicUser
  access_token: string
}

export interface Company {
  id: number
  ticker: string
  name: string
  sector: string | null
  currency: string
  market: string
  exchange: string | null
  cik: string | null
}

export type ModelKind = 'dcf' | 'ddm' | 'graham' | 'multiples'

export interface ValuationResult {
  model: ModelKind
  intrinsic_value: number
  current_price: number | null
  upside_pct: number | null
  verdict: string | null
  detail: Record<string, unknown>
  saved_id?: number
}

export interface SavedValuation {
  id: number
  company_id: number | null
  model: ModelKind | string
  inputs: Record<string, unknown>
  assumptions: Record<string, unknown>
  result: ValuationResult & {
    selected_scenario?: 'low' | 'base' | 'high'
    low?: number
    base?: number
    high?: number
    comparison?: { label?: string } | null
    availability_type?: string
  }
  us_company?: boolean
  ticker?: string | null
  model_version?: string | null
  user_price?: number | null
  created_at: string
}

// --- Portfolio-aware insights ---

export interface Holding {
  id: number
  company_id: number
  ticker: string
  name: string
  sector: string | null
  currency: string
  market: string
  exchange: string | null
}

export type InsightDirection = 'headwind' | 'tailwind' | 'mixed' | 'neutral'

export interface InsightSource {
  title: string | null
  url: string | null
}

export interface FeedInsight {
  id: number
  company_id: number
  ticker: string
  name: string
  sector: string | null
  summary: string
  possible_impact: string
  direction: InsightDirection | null
  confidence: number | null
  sources: InsightSource[]
  link_type: 'direct' | 'thematic'
  article_title: string
  article_url: string
  published_at: string | null
  created_at: string
}

// --- News feed (raw market news, pre-insight) ---

export interface NewsArticle {
  id: number
  source: string
  url: string
  title: string
  snippet: string | null
  published_at: string | null
}

// --- Research workbench (filing-based) ---

export type Sentiment = 'bear' | 'base' | 'bull'

export interface ResearchCompany {
  symbol: string
  name: string
  shortName: string | null
  sector: string | null
  subsector: string | null
  color: string | null
  insight: string | null
  source: { label: string; href: string } | null
  period: string | null
}

export interface RankedCompany extends ResearchCompany {
  score: number
  checks: { passes: number; total: number }
}

export interface RankingsResponse {
  risk: number
  profile: { label: string; short: string; tone: string }
  ranked: RankedCompany[]
}

export type MetricStatus = 'pass' | 'watch' | 'unavailable' | 'context'

export interface HealthMetric {
  key: string
  label: string
  description: string
  value: number | null
  target: number | null
  direction: 'min' | 'max' | 'range' | 'context'
  tolerance?: number
  format: 'percent' | 'multiple' | 'currency'
  status: MetricStatus
  score: number
}

export interface HealthResponse {
  company: ResearchCompany
  risk: number
  profile: { label: string; short: string; tone: string }
  pnl: HealthMetric[]
  balance: HealthMetric[]
}

export interface ValuationModel {
  perShare: number
  peerPe?: number
  discountRate?: number
  terminalGrowth?: number
  normalizedFcf?: number
}

export interface ResearchValuation {
  company: ResearchCompany
  sentiment: Sentiment
  weights: Record<string, number>
  valuationNote: string | null
  assumptions: {
    riskFreeRate: number
    grahamBaselineYield: number
    note: string
    sourceUrl: string
    sourceLabel: string
  }
  blended: number
  low: number
  high: number
  models: {
    dcf: ValuationModel
    graham: ValuationModel
    multiples: ValuationModel
    ddm: ValuationModel | null
  }
}

export interface SmartBrief {
  company: ResearchCompany
  risk: number
  sentiment: Sentiment
  headline: string
  score: number
  paragraphs: string[]
  passLabels: string[]
  watchLabels: string[]
}

// Governed, staged PSE V2 valuations. Scenario labels retain their economic
// meaning; numerical_range is a separate min/max and does not assume bear is low.
export type PseAvailabilityType = 'intrinsic_valuation' | 'market_relative_only' | 'not_available'
export type PsePublicationState = 'approved' | 'provisional' | 'blocked'

export interface PseScenarioValue {
  value_per_share: number
  common_equity_value: number
  enterprise_value: number | null
}

export interface PseValuationSummary {
  ticker: string
  name: string
  subsector: string
  primary_model: string
  base: number | null
  availability_type: PseAvailabilityType
  publication_state: PsePublicationState
  valuation_date: string
}

export interface PseValuationList {
  count: number
  items: PseValuationSummary[]
  catalog_version: string
  universe_version: string
  valuation_date: string
  catalog_status: 'staged' | 'active'
  artifact_count: number
}

export interface PseValuation {
  schema_version: string
  model_version: string
  ticker: string
  currency: 'PHP'
  issuer: { issuer_id: string; name: string }
  security: { security_id: string; type: string }
  subsector: string
  primary_model: string
  valuation_date: string
  filing_period: string | null
  filing_published_at: string | null
  price: { value?: number; date?: string; source?: string } | null
  availability_type: PseAvailabilityType
  publication_state: PsePublicationState
  scenarios: Record<'bear' | 'base' | 'bull', PseScenarioValue | null>
  numerical_range: { low: number | null; high: number | null }
  market_relative: {
    output_type: 'market_relative_only'
    metric: string
    relation: 'multiple' | 'yield'
    metric_label: string
    metric_value_per_share: number
    assumptions: Record<'low' | 'base' | 'high', number>
    estimates: Record<'low' | 'base' | 'high', number>
    policy_version: string
    source_status: string
    source_document_sha256: string
    source_page: number | null
    note: string
  } | null
  public_assumptions: Record<string, unknown>
  sensitivities: Array<Record<string, unknown>>
  sources: Array<{
    document_id: string
    label: string
    form: string | null
    period_end: string | null
    published_at: string | null
    url: string | null
    source_page: number | null
    sha256: string
  }>
  warnings: string[]
  blocking_reasons: string[]
  input_hash: string
  artifact_hash: string
  catalog: {
    catalog_version: string
    universe_version: string
    valuation_date: string
    catalog_status: 'staged' | 'active'
    artifact_count: number
    source_audit: string
  }
}

export interface PseCalculatorField {
  key: string
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: 'percent' | 'number' | 'multiple' | 'years'
}

export interface PseCalculatorView {
  ticker: string
  assigned_model: string
  model_version: string
  baseline_version?: string | null
  availability_type: PseAvailabilityType
  can_calculate: boolean
  defaults: Record<string, number>
  scenario_presets: Record<'low' | 'base' | 'high', Record<string, number>>
  scenario_preset_note: string
  editable_assumptions: PseCalculatorField[]
  locked_facts: string[]
  baseline_result: Record<'low' | 'base' | 'high', number> | null
  warnings: string[]
}

export interface PseCalculatorResult extends PseCalculatorView {
  selected_scenario: 'low' | 'base' | 'high'
  assumptions: Record<string, number>
  result: Record<'low' | 'base' | 'high', number>
  baseline_change_pct: number
  comparison: {
    status: 'available'
    source: 'manual'
    price: number
    gap_pct: number
    label: string
    verdict: 'undervalued' | 'overvalued' | 'fair_value'
  } | null
  manual_price: number | null
  saved_id?: number
}

export interface PseValuationHistory {
  ticker: string
  items: Array<{
    catalog_version: string
    valuation_date: string
    availability_type: PseAvailabilityType
    publication_state: PsePublicationState
    range: { low: number | null; base: number | null; high: number | null }
    filing_period: string | null
  }>
}

// Filing-only U.S. valuations served by GET /api/us-valuations/{ticker}.
// The public artifact is price-free by design: no reported statement amounts,
// no market price, no buy/hold/sell label — only derived intrinsic values,
// governed assumptions, and provenance. Fields are optional/loose because the
// artifact carries provenance the UI shows opportunistically.
export type UsPublicationState = 'pass' | 'review_required' | 'withheld' | null
export type UsAvailabilityType = 'available' | 'conditional_estimate' | 'not_available'

export interface UsModelResult {
  model: string
  output_type: string
  currency: string
  intrinsic_value_per_share: number | null
  conditional_value_per_share?: number | null
  publication_state: UsPublicationState
  errors: string[]
  warnings: string[]
}

export interface UsSegmentAssumption {
  label: string
  initial_revenue_growth?: number | null
  target_operating_margin?: number | null
  target_gross_margin?: number | null
}

export interface UsValuation {
  freshness?: { outcome: string; checked_as_of?: string; reason?: string | null }
  normalization_explanation?: string
  model_version?: string
  assumption_date?: string
  dates?: { filing_period: string; evidence_cutoff: string; assumption_date: string | null; market_comparison_date: string | null }
  schema_version: string
  valuation_date: string
  market: string
  currency: string
  ticker: string
  availability_type: UsAvailabilityType
  primary_valuation_method?: string
  issuer: {
    cik: string
    ticker: string
    issuer_name: string
    finsight_sector: string
    primary_archetype: string
    secondary_archetypes: string[]
    classification_confidence: number
    classification_reason?: string
  }
  source_financial_statement: {
    form: string
    period_end: string
    filed_date: string
    accession: string
    url: string
    note?: string
  }
  model_policy: { primary: string; supporting: string[]; blend_models: boolean; reason?: string }
  public_assumptions: {
    normalization_basis?: string
    forecast_years: number
    forecast_mode?: string
    initial_revenue_growth?: number | null
    target_operating_margin?: number | null
    segment_assumptions?: Record<string, UsSegmentAssumption>
    terminal_growth: number
    policy_wacc: number
    risk_free_rate: number
    risk_free_effective_date?: string
    risk_free_source_url?: string
    equity_risk_premium: number
  }
  models: Record<string, UsModelResult>
  scenarios: Record<string, Record<string, UsModelResult>>
  scenario_range: { low: number; base: number; high: number; label?: string }
  review?: { publication_state: UsPublicationState; errors?: string[]; warnings?: string[] }
  reliability?: {
    label?: 'High' | 'Medium' | 'Low'
    source_cap?: 'High' | 'Medium' | 'Low'
    accounting_label?: 'High' | 'Medium' | 'Low'
    scenario_label?: 'High' | 'Medium' | 'Low'
    reasons?: string[]
  }
  evidence_health?: Array<{
    key: string
    label: string
    score: number | null
    band: string
    methodology_version: string
  }>
  catalog?: {
    catalog_version: string
    universe_version: string
    valuation_date: string
    included_batches: number[]
    artifact_count: number
    batch: number
    source_audit: string
  }
  methodology?: string
  // Machine-readable public-safety attestation baked into every artifact.
  data_boundary?: {
    raw_financial_statement_values_included: boolean
    stock_prices_used: boolean
    public_payload_contains: string
  }
}

export interface UsValuationSummary {
  ticker: string
  name: string | null
  sector: string | null
  model: string | null
  base: number | null
  publication_state: UsPublicationState
  availability_type: UsAvailabilityType
  reliability: string | null
  batch: number
}

export interface UsValuationList {
  count: number
  items: UsValuationSummary[]
  catalog_version: string
  universe_version: string
  valuation_date: string
  included_batches: number[]
  artifact_count: number
}

export interface UsValuationHistory {
  ticker: string
  items: { catalog_version: string; valuation_date: string; availability_type: UsAvailabilityType; scenario_range: UsValuation['scenario_range']; source_financial_statement: UsValuation['source_financial_statement'] }[]
}

export interface UsCalculatorField {
  key: string
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: 'percent' | 'number' | 'multiple' | 'years'
}

export interface UsCalculatorView {
  baseline_version?: string
  recipe_version?: string | null
  recipe_hash?: string | null
  calculation_mode?: 'exact_recipe' | 'legacy_sensitivity'
  ticker: string
  assigned_model: string
  model_family?: string
  model_version: string
  availability_type: UsAvailabilityType
  can_calculate: boolean
  defaults: Record<string, number>
  scenario_presets?: Partial<Record<'low' | 'base' | 'high', Record<string, number>>>
  scenario_preset_note?: string
  editable_assumptions: UsCalculatorField[]
  locked_facts: string[]
  baseline_result: { low: number | null; base: number | null; high: number | null }
  warnings: string[]
}

export interface UsCalculatorResult extends UsCalculatorView {
  selected_scenario?: 'low' | 'base' | 'high'
  assumptions: Record<string, number>
  result: { low: number; base: number; high: number }
  baseline_change_pct: number
  comparison: {
    status: 'available'
    source: 'manual'
    price: number
    gap_pct: number
    label: string
    verdict: 'undervalued' | 'overvalued' | 'fair_value'
  } | null
  manual_price: number | null
  saved_id?: number
}
