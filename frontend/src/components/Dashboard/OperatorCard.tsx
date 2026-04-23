import StatusBadge from '../Common/StatusBadge';

interface OperatorCardProps {
  name: string;
  ticker: string | null;
  rating: string;
  outlook: string;
  debtToEbitda: number;
  occupancy: number;
  marketCap: number | null;
}

const ratingColor = (rating: string): string => {
  if (rating.startsWith('A') || rating === 'Aaa') return 'text-green-400';
  if (rating.startsWith('Baa')) return 'text-blue-400';
  if (rating.startsWith('Ba')) return 'text-amber-400';
  return 'text-red-400';
};

const outlookStatus = (outlook: string): 'active' | 'warning' | 'error' | 'info' => {
  if (outlook === 'POS') return 'active';
  if (outlook === 'STA') return 'info';
  if (outlook === 'NEG') return 'error';
  return 'warning';
};

export default function OperatorCard({
  name,
  ticker,
  rating,
  outlook,
  debtToEbitda,
  occupancy,
  marketCap,
}: OperatorCardProps) {
  return (
    <div className="gradient-border rounded-lg p-4 hover:bg-terminal-hover transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">{name}</h3>
          <p className="text-xs text-slate-500">{ticker ?? 'Private'}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`text-lg font-bold font-mono ${ratingColor(rating)}`}>{rating}</span>
          <StatusBadge status={outlookStatus(outlook)} label={outlook} />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Leverage</p>
          <p className="text-sm font-semibold text-slate-300">{debtToEbitda.toFixed(1)}x</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Occupancy</p>
          <p className="text-sm font-semibold text-slate-300">{(occupancy * 100).toFixed(0)}%</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Mkt Cap</p>
          <p className="text-sm font-semibold text-slate-300">
            {marketCap ? `$${(marketCap / 1000).toFixed(1)}B` : '—'}
          </p>
        </div>
      </div>
    </div>
  );
}
