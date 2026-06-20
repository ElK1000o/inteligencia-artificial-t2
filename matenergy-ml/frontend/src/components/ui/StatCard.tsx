import { ReactNode } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
  color?: 'cyan' | 'green' | 'yellow' | 'red' | 'blue';
}

const colorMap = {
  cyan: 'text-cyan-400 bg-cyan-500/10',
  green: 'text-green-400 bg-green-500/10',
  yellow: 'text-yellow-400 bg-yellow-500/10',
  red: 'text-red-400 bg-red-500/10',
  blue: 'text-blue-400 bg-blue-500/10',
};

export function StatCard({
  label,
  value,
  icon,
  trend,
  trendLabel,
  color = 'cyan',
}: StatCardProps) {
  return (
    <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
          {trend && trendLabel && (
            <div className="flex items-center gap-1 mt-2">
              {trend === 'up' && <TrendingUp size={12} className="text-green-400" />}
              {trend === 'down' && <TrendingDown size={12} className="text-red-400" />}
              {trend === 'neutral' && <Minus size={12} className="text-gray-400" />}
              <span className="text-xs text-gray-500">{trendLabel}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorMap[color]}`}>{icon}</div>
      </div>
    </div>
  );
}
