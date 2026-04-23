import { AlertTriangle, TrendingUp, Bell } from 'lucide-react';

interface Alert {
  id: string;
  type: 'rating_change' | 'market_event' | 'threshold';
  message: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'critical';
}

const mockAlerts: Alert[] = [
  {
    id: 'a-001',
    type: 'rating_change',
    message: "Moody's revised Digital Realty (DLR) outlook to Positive from Stable",
    timestamp: '2025-01-12T14:30:00Z',
    severity: 'info',
  },
  {
    id: 'a-002',
    type: 'market_event',
    message: 'CoreWeave priced $2.1B secured notes at 9.5% — largest speculative-grade DC issuance',
    timestamp: '2025-01-10T09:15:00Z',
    severity: 'warning',
  },
  {
    id: 'a-003',
    type: 'threshold',
    message: 'CyrusOne Debt/EBITDA reached 6.9x — approaching 7.0x covenant threshold',
    timestamp: '2025-01-09T11:00:00Z',
    severity: 'critical',
  },
  {
    id: 'a-004',
    type: 'rating_change',
    message: "Moody's affirmed Equinix (EQIX) at A3 with Stable outlook",
    timestamp: '2025-01-08T16:00:00Z',
    severity: 'info',
  },
];

const iconMap = {
  rating_change: Bell,
  market_event: TrendingUp,
  threshold: AlertTriangle,
};

const severityColors = {
  info: 'border-l-blue-500 bg-blue-500/5',
  warning: 'border-l-amber-500 bg-amber-500/5',
  critical: 'border-l-red-500 bg-red-500/5',
};

export default function AlertsPanel() {
  return (
    <div className="gradient-border rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300">Recent Alerts</h3>
        <span className="text-xs text-slate-500">{mockAlerts.length} alerts</span>
      </div>
      <div className="space-y-3">
        {mockAlerts.map((alert) => {
          const Icon = iconMap[alert.type];
          return (
            <div
              key={alert.id}
              className={`border-l-2 rounded-r-lg px-4 py-3 ${severityColors[alert.severity]}`}
            >
              <div className="flex items-start gap-3">
                <Icon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-300 leading-relaxed">{alert.message}</p>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {new Date(alert.timestamp).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
