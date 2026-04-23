import { NavLink, Outlet } from 'react-router-dom';
import {
  MessageSquare,
  LayoutDashboard,
  Link2,
  Activity,
  Database,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: MessageSquare, label: 'Chat' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/workato', icon: Link2, label: 'Workato' },
  { to: '/arize', icon: Activity, label: 'Arize' },
];

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 lg:w-56 flex-shrink-0 bg-terminal-surface border-r border-terminal-border flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center gap-2.5 px-4 border-b border-terminal-border">
          <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
            <Database className="w-4 h-4 text-blue-400" />
          </div>
          <div className="hidden lg:block">
            <p className="text-sm font-semibold text-slate-100 leading-tight">DC Investments</p>
            <p className="text-[10px] text-slate-500 leading-tight">Agent MVP</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 px-2 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-500/10 text-blue-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-terminal-hover'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="hidden lg:inline">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-terminal-border">
          <div className="hidden lg:flex items-center gap-2 px-2">
            <div className="w-2 h-2 rounded-full bg-green-400" />
            <span className="text-xs text-slate-500">System Online</span>
          </div>
          <div className="lg:hidden flex justify-center">
            <div className="w-2 h-2 rounded-full bg-green-400" />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden bg-terminal-bg">
        <Outlet />
      </main>
    </div>
  );
}
