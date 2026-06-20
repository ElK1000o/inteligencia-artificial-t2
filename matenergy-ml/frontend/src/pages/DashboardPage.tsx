import { useEffect, useState } from 'react';
import {
  Atom,
  Database,
  Brain,
  Trophy,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Activity,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { StatCard } from '../components/ui/StatCard';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { getDashboardStats } from '../api/dashboard';
import { DashboardStats } from '../types';

const CHART_COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'];
const PIE_COLORS = { stable: '#10b981', unstable: '#ef4444', borderline: '#f59e0b' };

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then((r) => setStats(r.data))
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  const s = stats;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Panel de Control</h1>
        <p className="text-gray-400 text-sm mt-1">
          Resumen del cribado computacional de materiales energéticos
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total de Materiales"
          value={s?.total_materials ?? '—'}
          icon={<Atom size={20} />}
          color="cyan"
        />
        <StatCard
          label="Materiales Válidos"
          value={s?.valid_materials ?? '—'}
          icon={<CheckCircle2 size={20} />}
          color="green"
        />
        <StatCard
          label="Modelos Activos"
          value={s?.active_models ?? '—'}
          icon={<Brain size={20} />}
          color="blue"
        />
        <StatCard
          label="Materiales Estables (DFT)"
          value={s?.stable_candidates ?? '—'}
          icon={<Trophy size={20} />}
          color="yellow"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Datasets Cargados"
          value={s?.active_datasets ?? '—'}
          icon={<Database size={20} />}
          color="cyan"
        />
        <StatCard
          label="Filas Rechazadas"
          value={s?.rejected_rows ?? '—'}
          icon={<XCircle size={20} />}
          color="red"
        />
        <StatCard
          label="Mejor MAE"
          value={s?.best_mae != null ? s.best_mae.toFixed(4) : '—'}
          icon={<Activity size={20} />}
          color="blue"
        />
        <StatCard
          label="Eventos de Seguridad"
          value={s?.security_events_count ?? '—'}
          icon={<AlertTriangle size={20} />}
          color={s?.security_events_count ? 'red' : 'green'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Estado del Sistema">
          <div className="space-y-3 text-sm">
            <div className="flex justify-between items-center py-2 border-b border-navy-700">
              <span className="text-gray-400">Último Entrenamiento</span>
              <span className="text-gray-200">{s?.last_training ?? 'Ninguno'}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-navy-700">
              <span className="text-gray-400">Mejor F1 Score</span>
              <span className="text-gray-200">{s?.best_f1?.toFixed(4) ?? '—'}</span>
            </div>
          </div>
        </Card>

        <Card title="Acciones Rápidas">
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Subir Dataset', href: '/datasets' },
              { label: 'Entrenar Modelo', href: '/models' },
              { label: 'Generar Ranking', href: '/ranking' },
              { label: 'Ver Reportes', href: '/reports' },
            ].map(({ label, href }) => (
              <a
                key={href}
                href={href}
                className="bg-navy-700 hover:bg-navy-600 border border-navy-500 hover:border-cyan-400/50 rounded-lg p-3 text-sm text-center text-gray-300 hover:text-white transition-all"
              >
                {label}
              </a>
            ))}
          </div>
        </Card>
      </div>

      {/* Stability Overview Chart */}
      {s && (s.valid_materials > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card title="Resumen de Estabilidad">
            <div className="text-xs text-gray-500 mb-3">
              Basado en el umbral energy_above_hull ≤ 0.05 eV/átomo
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'Estable', value: s.stable_candidates },
                    { name: 'No Estable', value: Math.max(0, s.valid_materials - s.stable_candidates) },
                  ]}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  <Cell fill={PIE_COLORS.stable} />
                  <Cell fill={PIE_COLORS.unstable} />
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#1e3a5f', border: '1px solid #334155', borderRadius: '8px' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Calidad del Dataset">
            <div className="text-xs text-gray-500 mb-3">
              Filas válidas vs. rechazadas en todos los datasets
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={[
                  { name: 'Válidas', count: s.valid_materials, fill: '#10b981' },
                  { name: 'Rechazadas', count: s.rejected_rows, fill: '#ef4444' },
                ]}
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#1e3a5f', border: '1px solid #334155', borderRadius: '8px' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {[{ fill: '#10b981' }, { fill: '#ef4444' }].map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}
    </div>
  );
}
