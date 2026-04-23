import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  color?: 'blue' | 'green' | 'red' | 'amber' | 'slate';
}

const colorMap = {
  blue: 'text-blue-400',
  green: 'text-green-400',
  red: 'text-red-400',
  amber: 'text-amber-400',
  slate: 'text-slate-300',
};

const bgMap = {
  blue: 'bg-blue-500/10',
  green: 'bg-green-500/10',
  red: 'bg-red-500/10',
  amber: 'bg-amber-500/10',
  slate: 'bg-slate-500/10',
};

export default function MetricCard({
  label,
  value,
  subtext,
  icon,
  trend,
  color = 'blue',
}: MetricCardProps) {
  return (
    <div className="gradient-border rounded-lg p-4 hover:bg-terminal-hover transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className={`text-2xl font-semibold ${colorMap[color]}`}>{value}</p>
          {subtext && (
            <p className="text-xs text-slate-500 mt-1">{subtext}</p>
          )}
        </div>
        {icon && (
          <div className={`p-2 rounded-lg ${bgMap[color]}`}>
            {icon}
          </div>
        )}
      </div>
      {trend && (
        <div className="mt-2 flex items-center gap-1 text-xs">
          {trend === 'up' && <span className="text-green-400">▲</span>}
          {trend === 'down' && <span className="text-red-400">▼</span>}
          {trend === 'neutral' && <span className="text-slate-500">—</span>}
          <span className="text-slate-500">vs prior period</span>
        </div>
      )}
    </div>
  );
}
