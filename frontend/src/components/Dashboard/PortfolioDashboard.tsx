import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { LayoutDashboard } from 'lucide-react';
import OperatorCard from './OperatorCard';
import RiskSummary from './RiskSummary';
import AlertsPanel from './AlertsPanel';
import type { DataCenterOperator, CreditRating, FinancialMetrics } from '../../types';

// ─── Demo Data ───────────────────────────────────────────────────────────────

const operators: (DataCenterOperator & { outlook: CreditRating['outlook'] })[] = [
  { id: 'op-001', name: 'Equinix Inc.',        ticker: 'EQIX', moodys_rating: 'A3',   sector: 'Data Center REIT', hq: 'US', market_cap: 74200, outlook: 'STA' },
  { id: 'op-002', name: 'Digital Realty Trust', ticker: 'DLR',  moodys_rating: 'Baa2', sector: 'Data Center REIT', hq: 'US', market_cap: 38500, outlook: 'POS' },
  { id: 'op-003', name: 'QTS Realty Trust',     ticker: null,   moodys_rating: 'Ba2',  sector: 'Data Center',      hq: 'US', market_cap: null,  outlook: 'STA' },
  { id: 'op-004', name: 'CyrusOne LLC',         ticker: null,   moodys_rating: 'Ba3',  sector: 'Data Center',      hq: 'US', market_cap: null,  outlook: 'NEG' },
  { id: 'op-005', name: 'CoreSite Realty',      ticker: 'COR',  moodys_rating: 'Baa3', sector: 'Data Center REIT', hq: 'US', market_cap: 8400,  outlook: 'STA' },
  { id: 'op-006', name: 'Switch Inc.',          ticker: 'SWCH', moodys_rating: 'B1',   sector: 'Data Center',      hq: 'US', market_cap: 7900,  outlook: 'STA' },
];

const latestMetrics: Record<string, FinancialMetrics> = {
  'op-001': { operator_id: 'op-001', period: '2024-Q2', revenue: 2085, ebitda: 991, ffo: 855, debt_to_ebitda: 3.7, interest_coverage: 5.3, occupancy_rate: 0.93, capex: 740, liquidity: 4650 },
  'op-002': { operator_id: 'op-002', period: '2024-Q2', revenue: 1385, ebitda: 710, ffo: 592, debt_to_ebitda: 5.7, interest_coverage: 3.5, occupancy_rate: 0.86, capex: 545, liquidity: 2950 },
  'op-003': { operator_id: 'op-003', period: '2024-Q2', revenue: 445,  ebitda: 210, ffo: 172, debt_to_ebitda: 6.5, interest_coverage: 2.7, occupancy_rate: 0.89, capex: 325, liquidity: 950 },
  'op-004': { operator_id: 'op-004', period: '2024-Q2', revenue: 395,  ebitda: 184, ffo: 148, debt_to_ebitda: 6.9, interest_coverage: 2.4, occupancy_rate: 0.83, capex: 295, liquidity: 700 },
  'op-005': { operator_id: 'op-005', period: '2024-Q2', revenue: 192,  ebitda: 107, ffo: 92,  debt_to_ebitda: 4.1, interest_coverage: 4.1, occupancy_rate: 0.95, capex: 100, liquidity: 545 },
  'op-006': { operator_id: 'op-006', period: '2024-Q2', revenue: 175,  ebitda: 84,  ffo: 67,  debt_to_ebitda: 5.3, interest_coverage: 3.0, occupancy_rate: 0.81, capex: 235, liquidity: 410 },
};

const leverageData = operators.map((op) => ({
  name: op.ticker ?? op.name.split(' ')[0],
  'Debt/EBITDA': latestMetrics[op.id].debt_to_ebitda,
  rating: op.moodys_rating,
}));

const occupancyTrends = [
  { period: 'Q1-23', EQIX: 91, DLR: 83, QTS: 86, COR: 93, SWCH: 78 },
  { period: 'Q2-23', EQIX: 91, DLR: 84, QTS: 87, COR: 93, SWCH: 79 },
  { period: 'Q3-23', EQIX: 92, DLR: 84, QTS: 87, COR: 94, SWCH: 79 },
  { period: 'Q4-23', EQIX: 92, DLR: 85, QTS: 88, COR: 94, SWCH: 80 },
  { period: 'Q1-24', EQIX: 92, DLR: 85, QTS: 88, COR: 94, SWCH: 80 },
  { period: 'Q2-24', EQIX: 93, DLR: 86, QTS: 89, COR: 95, SWCH: 81 },
];

const chartTooltipStyle = {
  contentStyle: {
    backgroundColor: '#1c2030',
    border: '1px solid #2a2f42',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#cbd5e1',
  },
  labelStyle: { color: '#94a3b8' },
};

// ─── Component ───────────────────────────────────────────────────────────────

export default function PortfolioDashboard() {
  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-terminal-border bg-terminal-surface/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="w-5 h-5 text-blue-400" />
          <h1 className="text-sm font-semibold text-slate-200">Portfolio Dashboard</h1>
          <span className="text-xs text-slate-500">6 issuers</span>
        </div>
        <span className="text-xs text-slate-600">Last updated: Jan 15, 2025 08:30 UTC</span>
      </header>

      <div className="p-6 space-y-6">
        {/* Top Section: Watchlist + Risk Summary */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Watchlist */}
          <div className="xl:col-span-2">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Watchlist
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {operators.map((op) => {
                const m = latestMetrics[op.id];
                return (
                  <OperatorCard
                    key={op.id}
                    name={op.name}
                    ticker={op.ticker}
                    rating={op.moodys_rating}
                    outlook={op.outlook}
                    debtToEbitda={m.debt_to_ebitda}
                    occupancy={m.occupancy_rate}
                    marketCap={op.market_cap}
                  />
                );
              })}
            </div>
          </div>

          {/* Risk Summary */}
          <div>
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
              Portfolio Risk
            </h2>
            <RiskSummary
              weightedAvgRating="Baa2"
              topConcentration={{ name: 'EQIX', pct: 22 }}
              geoConcentration={{ region: 'N. Virginia', pct: 38 }}
              avgLeverage={5.4}
              esgFlags={1}
            />
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Leverage Comparison */}
          <div className="gradient-border rounded-lg p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">
              Leverage Comparison (Debt/EBITDA) — Q2 2024
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={leverageData} barSize={36}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2f42" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#2a2f42' }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#2a2f42' }} domain={[0, 8]} />
                <Tooltip {...chartTooltipStyle} />
                <Bar dataKey="Debt/EBITDA" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Occupancy Trends */}
          <div className="gradient-border rounded-lg p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">
              Occupancy Trends (%)
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={occupancyTrends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2f42" />
                <XAxis dataKey="period" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#2a2f42' }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={{ stroke: '#2a2f42' }} domain={[70, 100]} />
                <Tooltip {...chartTooltipStyle} />
                <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
                <Line type="monotone" dataKey="EQIX" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="DLR" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="QTS" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="COR" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="SWCH" stroke="#ef4444" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Alerts */}
        <AlertsPanel />
      </div>
    </div>
  );
}
