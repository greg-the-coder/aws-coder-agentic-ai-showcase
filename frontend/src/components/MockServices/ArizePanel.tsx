import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import {
  Activity, Clock, Zap, Target, DollarSign, AlertTriangle,
  RefreshCw, ChevronDown, ChevronRight,
} from 'lucide-react';
import MetricCard from '../Common/MetricCard';
import StatusBadge from '../Common/StatusBadge';
import DataTable from '../Common/DataTable';
import * as arizeService from '../../services/arize';
import type { ArizeDashboard as DashboardData, ArizeTrace } from '../../types';

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

function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function ArizePanel() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const d = await arizeService.getDashboard();
      setData(d);
      setLoading(false);
    }
    load();
  }, []);

  if (loading || !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
      </div>
    );
  }

  const latencyChartData = data.latency_over_time.map((p) => ({
    time: formatTime(p.timestamp),
    'Avg (ms)': Math.round(p.avg_ms),
    'P95 (ms)': Math.round(p.p95_ms),
  }));

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-terminal-border bg-terminal-surface/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Activity className="w-5 h-5 text-violet-400" />
          <h1 className="text-sm font-semibold text-slate-200">Arize LLM Observability</h1>
          <span className="ml-2 text-[10px] font-medium text-violet-400 bg-violet-500/10 border border-violet-500/20 rounded-full px-2.5 py-0.5">
            MOCK SERVICE
          </span>
        </div>
        <span className="text-xs text-slate-500 font-mono">dc-investments-agent</span>
      </header>

      <div className="p-6 space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <MetricCard
            label="Avg Latency"
            value={`${(data.metrics.avg_latency_ms / 1000).toFixed(2)}s`}
            icon={<Clock className="w-4 h-4 text-blue-400" />}
            color="blue"
          />
          <MetricCard
            label="P95 Latency"
            value={`${(data.metrics.p95_latency_ms / 1000).toFixed(2)}s`}
            icon={<Zap className="w-4 h-4 text-amber-400" />}
            color="amber"
          />
          <MetricCard
            label="Total Traces"
            value={data.metrics.total_traces.toLocaleString()}
            subtext={`${data.metrics.traces_last_24h} last 24h`}
            icon={<Activity className="w-4 h-4 text-blue-400" />}
            color="blue"
          />
          <MetricCard
            label="Accuracy Score"
            value={`${(data.metrics.accuracy_score * 100).toFixed(1)}%`}
            icon={<Target className="w-4 h-4 text-green-400" />}
            color="green"
          />
          <MetricCard
            label="Token Cost"
            value={`$${data.metrics.total_token_cost_usd.toFixed(2)}`}
            subtext="cumulative"
            icon={<DollarSign className="w-4 h-4 text-amber-400" />}
            color="amber"
          />
        </div>

        {/* Latency Chart + Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 gradient-border rounded-lg p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Latency Over Time (24h)</h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={latencyChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2f42" />
                <XAxis
                  dataKey="time"
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  axisLine={{ stroke: '#2a2f42' }}
                  interval={3}
                />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#2a2f42' }} />
                <Tooltip {...chartTooltipStyle} />
                <Legend wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }} />
                <Line type="monotone" dataKey="Avg (ms)" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="P95 (ms)" stroke="#f59e0b" strokeWidth={2} dot={false} strokeDasharray="5 3" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Alerts */}
          <div className="gradient-border rounded-lg p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Active Alerts</h3>
            <div className="space-y-3">
              {data.alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`rounded-lg p-3 border ${
                    alert.severity === 'warning'
                      ? 'bg-amber-500/5 border-amber-500/20'
                      : alert.severity === 'critical'
                      ? 'bg-red-500/5 border-red-500/20'
                      : 'bg-blue-500/5 border-blue-500/20'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle
                      className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${
                        alert.severity === 'warning'
                          ? 'text-amber-400'
                          : alert.severity === 'critical'
                          ? 'text-red-400'
                          : 'text-blue-400'
                      }`}
                    />
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-slate-300">{alert.type}</span>
                        <StatusBadge status={alert.severity} />
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">{alert.message}</p>
                      <p className="text-[10px] text-slate-600 mt-1">{formatTime(alert.timestamp)}</p>
                    </div>
                  </div>
                </div>
              ))}
              {data.alerts.length === 0 && (
                <p className="text-xs text-slate-500 text-center py-4">No active alerts</p>
              )}
            </div>
          </div>
        </div>

        {/* Evaluations Table */}
        <div>
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Evaluation Results
          </h2>
          <div className="gradient-border rounded-lg overflow-hidden">
            <DataTable
              columns={[
                {
                  key: 'eval_id',
                  header: 'Eval ID',
                  render: (row) => <span className="font-mono text-xs text-slate-500">{String(row.eval_id)}</span>,
                },
                {
                  key: 'trace_id',
                  header: 'Trace',
                  render: (row) => <span className="font-mono text-xs text-blue-400">{String(row.trace_id)}</span>,
                },
                {
                  key: 'relevance',
                  header: 'Relevance',
                  align: 'center' as const,
                  render: (row) => {
                    const v = Number(row.relevance);
                    return (
                      <span className={v >= 0.9 ? 'text-green-400' : v >= 0.7 ? 'text-amber-400' : 'text-red-400'}>
                        {(v * 100).toFixed(0)}%
                      </span>
                    );
                  },
                },
                {
                  key: 'faithfulness',
                  header: 'Faithfulness',
                  align: 'center' as const,
                  render: (row) => {
                    const v = Number(row.faithfulness);
                    return (
                      <span className={v >= 0.9 ? 'text-green-400' : v >= 0.7 ? 'text-amber-400' : 'text-red-400'}>
                        {(v * 100).toFixed(0)}%
                      </span>
                    );
                  },
                },
                {
                  key: 'toxicity',
                  header: 'Toxicity',
                  align: 'center' as const,
                  render: (row) => {
                    const v = Number(row.toxicity);
                    return (
                      <span className={v <= 0.05 ? 'text-green-400' : v <= 0.1 ? 'text-amber-400' : 'text-red-400'}>
                        {(v * 100).toFixed(1)}%
                      </span>
                    );
                  },
                },
                {
                  key: 'overall',
                  header: 'Overall',
                  align: 'center' as const,
                  render: (row) => {
                    const v = Number(row.overall);
                    return (
                      <span className={`font-semibold ${v >= 0.9 ? 'text-green-400' : v >= 0.7 ? 'text-amber-400' : 'text-red-400'}`}>
                        {(v * 100).toFixed(0)}%
                      </span>
                    );
                  },
                },
              ]}
              data={data.evaluations as unknown as Record<string, unknown>[]}
              keyField="eval_id"
              compact
            />
          </div>
        </div>

        {/* Traces Table */}
        <div>
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Recent Traces
          </h2>
          <div className="gradient-border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-terminal-border">
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-8" />
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Trace ID</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Agent</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Latency</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Tokens</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Cost</th>
                    <th className="px-3 py-2 text-center text-xs font-semibold text-slate-500 uppercase tracking-wider">Feedback</th>
                  </tr>
                </thead>
                <tbody>
                  {data.traces.map((trace: ArizeTrace) => (
                    <>
                      <tr
                        key={trace.trace_id}
                        className="border-b border-terminal-border/30 hover:bg-terminal-hover/50 transition-colors cursor-pointer"
                        onClick={() =>
                          setExpandedTrace(expandedTrace === trace.trace_id ? null : trace.trace_id)
                        }
                      >
                        <td className="px-3 py-2">
                          {expandedTrace === trace.trace_id ? (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                          )}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-blue-400">{trace.trace_id}</td>
                        <td className="px-3 py-2 text-sm text-slate-300">{trace.agent_name}</td>
                        <td className="px-3 py-2 text-sm text-slate-400">{trace.action}</td>
                        <td className="px-3 py-2 text-sm text-slate-300 text-right">
                          {trace.latency_ms < 1000
                            ? `${trace.latency_ms}ms`
                            : `${(trace.latency_ms / 1000).toFixed(2)}s`}
                        </td>
                        <td className="px-3 py-2 text-sm text-slate-400 text-right">{trace.token_count}</td>
                        <td className="px-3 py-2 text-sm text-slate-400 text-right">${trace.cost_usd.toFixed(4)}</td>
                        <td className="px-3 py-2 text-center">
                          {trace.feedback === 'up' && <span className="text-green-400">👍</span>}
                          {trace.feedback === 'down' && <span className="text-red-400">👎</span>}
                          {!trace.feedback && <span className="text-slate-600">—</span>}
                        </td>
                      </tr>
                      {expandedTrace === trace.trace_id && (
                        <tr key={`${trace.trace_id}-detail`} className="bg-terminal-bg/50">
                          <td colSpan={8} className="px-6 py-4">
                            <div className="grid grid-cols-2 gap-4 text-xs">
                              <div>
                                <p className="text-slate-500 uppercase tracking-wider mb-1">Input</p>
                                <p className="text-slate-300 bg-terminal-card rounded-lg p-3 font-mono">
                                  {trace.input_preview}
                                </p>
                              </div>
                              <div>
                                <p className="text-slate-500 uppercase tracking-wider mb-1">Output</p>
                                <p className="text-slate-300 bg-terminal-card rounded-lg p-3 font-mono">
                                  {trace.output_preview}
                                </p>
                              </div>
                              <div>
                                <p className="text-slate-500 uppercase tracking-wider mb-1">Session</p>
                                <p className="text-slate-400 font-mono">{trace.session_id}</p>
                              </div>
                              <div>
                                <p className="text-slate-500 uppercase tracking-wider mb-1">Timestamp</p>
                                <p className="text-slate-400">{new Date(trace.timestamp).toLocaleString()}</p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
