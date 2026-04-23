// ─── Core Domain Types ───────────────────────────────────────────────────────

export interface DataCenterOperator {
  id: string;
  name: string;
  ticker: string | null;
  moodys_rating: string;
  sector: string;
  hq: string;
  market_cap: number | null;
}

export interface CreditRating {
  operator_id: string;
  rating: string;
  outlook: 'POS' | 'NEG' | 'STA' | 'DEV';
  watch_status: 'UPG' | 'DNG' | 'UNC' | null;
  rating_date: string;
  previous_rating: string | null;
  analyst: string;
}

export interface FinancialMetrics {
  operator_id: string;
  period: string;
  revenue: number;
  ebitda: number;
  ffo: number;
  debt_to_ebitda: number;
  interest_coverage: number;
  occupancy_rate: number;
  capex: number;
  liquidity: number;
}

export interface MarketData {
  market_id: string;
  region: 'NA' | 'EMEA' | 'APAC' | 'LATAM';
  market_name: string;
  total_capacity_mw: number;
  absorption_rate: number;
  vacancy_rate: number;
  avg_price_per_kw: number;
  construction_pipeline_mw: number;
  yoy_growth: number;
}

export interface ESGProfile {
  operator_id: string;
  pue: number;
  carbon_intensity: number;
  renewable_pct: number;
  water_usage: number;
  climate_risk_score: number;
  green_bond_outstanding: number;
}

// ─── Chat / Session Types ────────────────────────────────────────────────────

export type FeedbackType = 'up' | 'down';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: string[];
  suggestions?: string[];
  feedback?: FeedbackType | null;
  traceId?: string;
}

export interface ChatSession {
  session_id: string;
  user_id: string;
  agent_id: string;
  messages: ChatMessage[];
  created_at: string;
  metadata: Record<string, string>;
}

export interface AgentResponse {
  session_id?: string;
  message?: string;
  response?: string;
  source?: string;
  sources?: string[];
  suggestions?: string[];
  trace_id?: string;
  latency_ms?: number;
  timestamp?: string;
}

// ─── Workato Types ───────────────────────────────────────────────────────────

export interface WorkatoRecipeStatus {
  recipe_id: string;
  name: string;
  status: 'active' | 'stopped' | 'error';
  last_run: string;
  next_run: string;
  success_count: number;
  error_count: number;
  avg_duration_ms: number;
}

export interface WorkatoConnection {
  id: string;
  name: string;
  provider: string;
  status: 'connected' | 'disconnected' | 'error';
  last_tested: string;
}

// ─── Arize Types ─────────────────────────────────────────────────────────────

export interface ArizeTrace {
  trace_id: string;
  session_id: string;
  agent_name: string;
  action: string;
  input_preview: string;
  output_preview: string;
  latency_ms: number;
  token_count: number;
  cost_usd: number;
  timestamp: string;
  feedback?: FeedbackType | null;
}

export interface ArizeMetrics {
  avg_latency_ms: number;
  p95_latency_ms: number;
  total_traces: number;
  accuracy_score: number;
  total_token_cost_usd: number;
  traces_last_24h: number;
  error_rate: number;
}

export interface ArizeDashboard {
  metrics: ArizeMetrics;
  latency_over_time: { timestamp: string; avg_ms: number; p95_ms: number }[];
  traces: ArizeTrace[];
  evaluations: ArizeEvaluation[];
  alerts: { id: string; type: string; message: string; severity: 'info' | 'warning' | 'critical'; timestamp: string }[];
}

export interface ArizeEvaluation {
  eval_id: string;
  trace_id: string;
  relevance: number;
  faithfulness: number;
  toxicity: number;
  overall: number;
  timestamp: string;
}
