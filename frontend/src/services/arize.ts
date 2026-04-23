import type { ArizeTrace, ArizeMetrics, ArizeDashboard, ArizeEvaluation } from '../types';

// ─── Mock Data ───────────────────────────────────────────────────────────────

const mockMetrics: ArizeMetrics = {
  avg_latency_ms: 2340,
  p95_latency_ms: 5870,
  total_traces: 12847,
  accuracy_score: 0.943,
  total_token_cost_usd: 284.52,
  traces_last_24h: 487,
  error_rate: 0.012,
};

function generateLatencyTimeline() {
  const points = [];
  const now = Date.now();
  for (let i = 23; i >= 0; i--) {
    const ts = new Date(now - i * 3600000).toISOString();
    points.push({
      timestamp: ts,
      avg_ms: 1800 + Math.random() * 1200,
      p95_ms: 4200 + Math.random() * 2400,
    });
  }
  return points;
}

const mockTraces: ArizeTrace[] = [
  { trace_id: 'tr-001', session_id: 'sess-a1', agent_name: 'Supervisor', action: 'route_query', input_preview: 'Compare leverage for EQIX and DLR', output_preview: 'Routing to Financial Sub-Agent...', latency_ms: 320, token_count: 245, cost_usd: 0.0041, timestamp: '2025-01-15T08:30:00Z', feedback: 'up' },
  { trace_id: 'tr-002', session_id: 'sess-a1', agent_name: 'Financial Sub-Agent', action: 'compute_leverage', input_preview: 'operators=[EQIX, DLR], metric=debt_to_ebitda', output_preview: 'EQIX: 3.7x, DLR: 5.7x (Q2-2024)', latency_ms: 2150, token_count: 890, cost_usd: 0.0148, timestamp: '2025-01-15T08:30:01Z', feedback: 'up' },
  { trace_id: 'tr-003', session_id: 'sess-b2', agent_name: 'Supervisor', action: 'route_query', input_preview: 'Show ESG profile for Switch', output_preview: 'Routing to ESG Sub-Agent...', latency_ms: 280, token_count: 210, cost_usd: 0.0035, timestamp: '2025-01-15T08:25:00Z', feedback: null },
  { trace_id: 'tr-004', session_id: 'sess-b2', agent_name: 'ESG Sub-Agent', action: 'get_esg_profile', input_preview: 'operator=Switch Inc.', output_preview: 'PUE: 1.18, Renewable: 100%, CIS: 88', latency_ms: 1870, token_count: 720, cost_usd: 0.0120, timestamp: '2025-01-15T08:25:01Z', feedback: 'up' },
  { trace_id: 'tr-005', session_id: 'sess-c3', agent_name: 'Supervisor', action: 'route_query', input_preview: 'What is market outlook for N. Virginia?', output_preview: 'Routing to Market Sub-Agent...', latency_ms: 310, token_count: 230, cost_usd: 0.0038, timestamp: '2025-01-15T08:15:00Z', feedback: null },
  { trace_id: 'tr-006', session_id: 'sess-c3', agent_name: 'Market Sub-Agent', action: 'analyze_market', input_preview: 'market=Northern Virginia', output_preview: '2,850 MW capacity, 3% vacancy, 18% YoY growth', latency_ms: 2430, token_count: 1050, cost_usd: 0.0175, timestamp: '2025-01-15T08:15:02Z', feedback: 'up' },
  { trace_id: 'tr-007', session_id: 'sess-d4', agent_name: 'Credit Sub-Agent', action: 'get_rating', input_preview: 'operator=CoreWeave', output_preview: 'No public Moody\'s rating found — emerging issuer', latency_ms: 980, token_count: 380, cost_usd: 0.0063, timestamp: '2025-01-15T07:50:00Z', feedback: 'down' },
  { trace_id: 'tr-008', session_id: 'sess-e5', agent_name: 'Financial Sub-Agent', action: 'compute_ffo', input_preview: 'operator=QTS, periods=Q1-Q2 2024', output_preview: 'FFO: $160M (Q1), $172M (Q2)', latency_ms: 1640, token_count: 560, cost_usd: 0.0093, timestamp: '2025-01-15T07:30:00Z', feedback: null },
];

const mockEvaluations: ArizeEvaluation[] = [
  { eval_id: 'ev-001', trace_id: 'tr-002', relevance: 0.95, faithfulness: 0.98, toxicity: 0.01, overall: 0.96, timestamp: '2025-01-15T08:30:05Z' },
  { eval_id: 'ev-002', trace_id: 'tr-004', relevance: 0.92, faithfulness: 0.95, toxicity: 0.00, overall: 0.94, timestamp: '2025-01-15T08:25:05Z' },
  { eval_id: 'ev-003', trace_id: 'tr-006', relevance: 0.97, faithfulness: 0.93, toxicity: 0.00, overall: 0.95, timestamp: '2025-01-15T08:15:05Z' },
  { eval_id: 'ev-004', trace_id: 'tr-007', relevance: 0.68, faithfulness: 0.72, toxicity: 0.02, overall: 0.70, timestamp: '2025-01-15T07:50:05Z' },
  { eval_id: 'ev-005', trace_id: 'tr-008', relevance: 0.91, faithfulness: 0.96, toxicity: 0.00, overall: 0.93, timestamp: '2025-01-15T07:30:05Z' },
];

const mockAlerts = [
  { id: 'alert-001', type: 'Eval Regression', message: 'Relevance score dropped below 0.80 threshold for Credit Sub-Agent (trace tr-007)', severity: 'warning' as const, timestamp: '2025-01-15T07:51:00Z' },
  { id: 'alert-002', type: 'Embedding Drift', message: 'Embedding drift detected in knowledge base index — cosine distance +0.12 from baseline', severity: 'info' as const, timestamp: '2025-01-14T22:00:00Z' },
];

// ─── Mock Client ─────────────────────────────────────────────────────────────

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function getTraces(params?: { limit?: number }): Promise<ArizeTrace[]> {
  await delay(300);
  const limit = params?.limit ?? 20;
  return mockTraces.slice(0, limit);
}

export async function getTrace(traceId: string): Promise<ArizeTrace | undefined> {
  await delay(200);
  return mockTraces.find((t) => t.trace_id === traceId);
}

export async function getEvaluations(): Promise<ArizeEvaluation[]> {
  await delay(250);
  return [...mockEvaluations];
}

export async function getMetrics(): Promise<ArizeMetrics> {
  await delay(200);
  return { ...mockMetrics };
}

export async function getDashboard(): Promise<ArizeDashboard> {
  await delay(400);
  return {
    metrics: { ...mockMetrics },
    latency_over_time: generateLatencyTimeline(),
    traces: [...mockTraces],
    evaluations: [...mockEvaluations],
    alerts: [...mockAlerts],
  };
}
