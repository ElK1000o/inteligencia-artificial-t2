import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  Atom,
  FlaskConical,
  Brain,
  Zap,
  Trophy,
  FileText,
  Shield,
  Settings,
  LogOut,
  Microscope,
  TerminalSquare,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Panel Principal' },
  { to: '/datasets', icon: Database, label: 'Conjuntos de Datos' },
  { to: '/materials', icon: Atom, label: 'Materiales' },
  { to: '/descriptors', icon: FlaskConical, label: 'Descriptores' },
  { to: '/models', icon: Brain, label: 'Modelos' },
  { to: '/predictions', icon: Zap, label: 'Predicciones' },
  { to: '/explore', icon: Microscope, label: 'Explorador' },
  { to: '/dft-jobs', icon: TerminalSquare, label: 'Trabajos DFT' },
  { to: '/ranking', icon: Trophy, label: 'Ranking' },
  { to: '/reports', icon: FileText, label: 'Reportes' },
  { to: '/admin', icon: Shield, label: 'Administración' },
  { to: '/settings', icon: Settings, label: 'Configuración' },
];

export function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 min-h-screen bg-navy-800 border-r border-navy-600 flex flex-col">
      <div className="p-6 border-b border-navy-600">
        <h1 className="text-xl font-bold text-cyan-400">MatEnergy-ML</h1>
        <p className="text-xs text-gray-400 mt-1">Cribado de Materiales con IA</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-cyan-500/20 text-cyan-400 font-medium'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-navy-600'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-navy-600">
        <div className="text-xs text-gray-500 mb-2">{user?.username}</div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-red-400 transition-colors"
        >
          <LogOut size={14} /> Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
