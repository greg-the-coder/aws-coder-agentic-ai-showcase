import { useState, useEffect } from 'react';
import { Link2, Play, RefreshCw, Zap, CheckCircle, XCircle, Clock } from 'lucide-react';
import MetricCard from '../Common/MetricCard';
import StatusBadge from '../Common/StatusBadge';
import DataTable from '../Common/DataTable';
import * as workatoService from '../../services/workato';
import type { WorkatoRecipeStatus, WorkatoConnection } from '../../types';

export default function WorkatoPanel() {
  const [recipes, setRecipes] = useState<WorkatoRecipeStatus[]>([]);
  const [connections, setConnections] = useState<WorkatoConnection[]>([]);
  const [runHistory, setRunHistory] = useState<{ id: string; recipe: string; status: 'success' | 'error'; started: string; duration_ms: number; records: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const [r, c, h] = await Promise.all([
        workatoService.getRecipes(),
        workatoService.getConnections(),
        workatoService.getRunHistory(),
      ]);
      setRecipes(r);
      setConnections(c);
      setRunHistory(h);
      setLoading(false);
    }
    load();
  }, []);

  const handleTrigger = async (recipeId: string) => {
    setTriggering(recipeId);
    await workatoService.triggerRecipe(recipeId);
    setTriggering(null);
  };

  const handleWebhook = async () => {
    await workatoService.simulateWebhook();
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <RefreshCw className="w-5 h-5 text-slate-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-6 border-b border-terminal-border bg-terminal-surface/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Link2 className="w-5 h-5 text-orange-400" />
          <h1 className="text-sm font-semibold text-slate-200">Workato Integration Hub</h1>
          <span className="ml-2 text-[10px] font-medium text-orange-400 bg-orange-500/10 border border-orange-500/20 rounded-full px-2.5 py-0.5">
            MOCK SERVICE
          </span>
        </div>
        <button
          onClick={handleWebhook}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 bg-terminal-card border border-terminal-border rounded-lg px-3 py-1.5 hover:bg-terminal-hover transition-colors"
        >
          <Zap className="w-3.5 h-3.5" />
          Simulate Webhook
        </button>
      </header>

      <div className="p-6 space-y-6">
        {/* Summary Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="Active Recipes"
            value={recipes.filter((r) => r.status === 'active').length}
            subtext={`of ${recipes.length} total`}
            icon={<Play className="w-4 h-4 text-green-400" />}
            color="green"
          />
          <MetricCard
            label="Total Runs (All Time)"
            value={recipes.reduce((sum, r) => sum + r.success_count + r.error_count, 0).toLocaleString()}
            icon={<CheckCircle className="w-4 h-4 text-blue-400" />}
            color="blue"
          />
          <MetricCard
            label="Error Rate"
            value={`${((recipes.reduce((sum, r) => sum + r.error_count, 0) / recipes.reduce((sum, r) => sum + r.success_count + r.error_count, 0)) * 100).toFixed(2)}%`}
            icon={<XCircle className="w-4 h-4 text-amber-400" />}
            color="amber"
          />
          <MetricCard
            label="Connections"
            value={`${connections.filter((c) => c.status === 'connected').length}/${connections.length}`}
            subtext="active"
            icon={<Link2 className="w-4 h-4 text-blue-400" />}
            color="blue"
          />
        </div>

        {/* Recipe Cards */}
        <div>
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Pipeline Recipes
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {recipes.map((recipe) => (
              <div key={recipe.recipe_id} className="gradient-border rounded-lg p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-200">{recipe.name}</h3>
                    <p className="text-[10px] text-slate-500 font-mono mt-0.5">{recipe.recipe_id}</p>
                  </div>
                  <StatusBadge status={recipe.status} />
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Success</p>
                    <p className="text-sm font-semibold text-green-400">{recipe.success_count.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Errors</p>
                    <p className="text-sm font-semibold text-red-400">{recipe.error_count}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Avg Duration</p>
                    <p className="text-sm font-semibold text-slate-300">{(recipe.avg_duration_ms / 1000).toFixed(1)}s</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Last Run</p>
                    <p className="text-sm font-semibold text-slate-300">
                      {new Date(recipe.last_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Clock className="w-3 h-3" />
                    Next: {new Date(recipe.next_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                  <button
                    onClick={() => handleTrigger(recipe.recipe_id)}
                    disabled={triggering === recipe.recipe_id}
                    className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-1.5 hover:bg-blue-500/20 transition-colors disabled:opacity-50"
                  >
                    {triggering === recipe.recipe_id ? (
                      <RefreshCw className="w-3 h-3 animate-spin" />
                    ) : (
                      <Play className="w-3 h-3" />
                    )}
                    Trigger
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Connections */}
        <div>
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Connection Status
          </h2>
          <div className="gradient-border rounded-lg overflow-hidden">
            <DataTable
              columns={[
                { key: 'name', header: 'Connection' },
                { key: 'provider', header: 'Provider' },
                {
                  key: 'status',
                  header: 'Status',
                  render: (row) => <StatusBadge status={(row as unknown as WorkatoConnection).status} />,
                },
                {
                  key: 'last_tested',
                  header: 'Last Tested',
                  render: (row) =>
                    new Date((row as unknown as WorkatoConnection).last_tested).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    }),
                },
              ]}
              data={connections as unknown as Record<string, unknown>[]}
              keyField="id"
            />
          </div>
        </div>

        {/* Run History */}
        <div>
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
            Recent Run History
          </h2>
          <div className="gradient-border rounded-lg overflow-hidden">
            <DataTable
              columns={[
                { key: 'id', header: 'Run ID', render: (row) => <span className="font-mono text-xs text-slate-500">{String(row.id)}</span> },
                { key: 'recipe', header: 'Recipe' },
                {
                  key: 'status',
                  header: 'Status',
                  render: (row) => <StatusBadge status={String(row.status) as 'success' | 'error'} />,
                },
                {
                  key: 'started',
                  header: 'Started',
                  render: (row) =>
                    new Date(String(row.started)).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    }),
                },
                {
                  key: 'duration_ms',
                  header: 'Duration',
                  align: 'right' as const,
                  render: (row) => `${(Number(row.duration_ms) / 1000).toFixed(1)}s`,
                },
                {
                  key: 'records',
                  header: 'Records',
                  align: 'right' as const,
                  render: (row) => Number(row.records).toLocaleString(),
                },
              ]}
              data={runHistory as unknown as Record<string, unknown>[]}
              keyField="id"
              compact
            />
          </div>
        </div>
      </div>
    </div>
  );
}
