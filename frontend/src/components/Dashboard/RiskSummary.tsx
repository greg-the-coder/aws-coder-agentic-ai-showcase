import { Shield, MapPin, BarChart3, Leaf } from 'lucide-react';

interface RiskSummaryProps {
  weightedAvgRating: string;
  topConcentration: { name: string; pct: number };
  geoConcentration: { region: string; pct: number };
  avgLeverage: number;
  esgFlags: number;
}

export default function RiskSummary({
  weightedAvgRating,
  topConcentration,
  geoConcentration,
  avgLeverage,
  esgFlags,
}: RiskSummaryProps) {
  const items = [
    {
      icon: Shield,
      label: 'Wtd-Avg Rating',
      value: weightedAvgRating,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    {
      icon: BarChart3,
      label: 'Top Concentration',
      value: `${topConcentration.name} (${topConcentration.pct}%)`,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
    },
    {
      icon: MapPin,
      label: 'Geo Concentration',
      value: `${geoConcentration.region} (${geoConcentration.pct}%)`,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10',
    },
    {
      icon: BarChart3,
      label: 'Avg Debt/EBITDA',
      value: `${avgLeverage.toFixed(1)}x`,
      color: 'text-slate-300',
      bg: 'bg-slate-500/10',
    },
    {
      icon: Leaf,
      label: 'ESG Flags',
      value: `${esgFlags} (CIS-4+)`,
      color: esgFlags > 0 ? 'text-amber-400' : 'text-green-400',
      bg: esgFlags > 0 ? 'bg-amber-500/10' : 'bg-green-500/10',
    },
  ];

  return (
    <div className="gradient-border rounded-lg p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">Risk Summary</h3>
      <div className="space-y-4">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg ${item.bg} flex items-center justify-center flex-shrink-0`}>
              <item.icon className={`w-4 h-4 ${item.color}`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider">{item.label}</p>
              <p className={`text-sm font-semibold ${item.color}`}>{item.value}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
