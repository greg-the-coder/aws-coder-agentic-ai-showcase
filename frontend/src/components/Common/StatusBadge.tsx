interface StatusBadgeProps {
  status: 'active' | 'connected' | 'success' | 'warning' | 'error' | 'disconnected' | 'stopped' | 'info' | 'critical';
  label?: string;
  size?: 'sm' | 'md';
}

const statusConfig: Record<string, { bg: string; text: string; dot: string }> = {
  active:       { bg: 'bg-green-500/10', text: 'text-green-400', dot: 'bg-green-400' },
  connected:    { bg: 'bg-green-500/10', text: 'text-green-400', dot: 'bg-green-400' },
  success:      { bg: 'bg-green-500/10', text: 'text-green-400', dot: 'bg-green-400' },
  warning:      { bg: 'bg-amber-500/10', text: 'text-amber-400', dot: 'bg-amber-400' },
  info:         { bg: 'bg-blue-500/10',  text: 'text-blue-400',  dot: 'bg-blue-400' },
  error:        { bg: 'bg-red-500/10',   text: 'text-red-400',   dot: 'bg-red-400' },
  disconnected: { bg: 'bg-red-500/10',   text: 'text-red-400',   dot: 'bg-red-400' },
  stopped:      { bg: 'bg-slate-500/10', text: 'text-slate-400', dot: 'bg-slate-400' },
  critical:     { bg: 'bg-red-500/10',   text: 'text-red-400',   dot: 'bg-red-400' },
};

export default function StatusBadge({ status, label, size = 'sm' }: StatusBadgeProps) {
  const cfg = statusConfig[status] ?? statusConfig.active;
  const displayLabel = label ?? status.charAt(0).toUpperCase() + status.slice(1);
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${cfg.bg} ${cfg.text} ${sizeClasses}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {displayLabel}
    </span>
  );
}
