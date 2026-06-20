import { useState } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
  Legend,
} from 'recharts';
import { Link } from 'react-router-dom';

export interface HullPoint {
  material_id: string;
  formula: string;
  formation_energy_per_atom: number | null;
  energy_above_hull: number | null;
  stability_label: 'stable' | 'metastable' | 'unstable' | 'unknown';
}

interface ConvexHullPlotProps {
  points: HullPoint[];
  overlayPoints?: { material_id: string; formula: string; x: number; y: number }[];
  height?: number;
}

const COLORS: Record<string, string> = {
  stable: '#10b981',
  metastable: '#f59e0b',
  unstable: '#ef4444',
  unknown: '#6b7280',
};

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { payload: HullPoint }[] }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-navy-800 border border-navy-500 rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="font-mono text-cyan-400 font-semibold">{d.formula}</div>
      <div className="text-gray-300 mt-1">
        Energía de formación: <span className="text-white">{d.formation_energy_per_atom?.toFixed(4)} eV/atom</span>
      </div>
      <div className="text-gray-300">
        Energía sobre el hull: <span className="text-white">{d.energy_above_hull?.toFixed(4)} eV/atom</span>
      </div>
      <div className="mt-1">
        <span
          className="px-1.5 py-0.5 rounded text-xs font-medium"
          style={{ background: COLORS[d.stability_label] + '33', color: COLORS[d.stability_label] }}
        >
          {d.stability_label}
        </span>
      </div>
    </div>
  );
};

export function ConvexHullPlot({ points, height = 380 }: ConvexHullPlotProps) {
  const [selected, setSelected] = useState<HullPoint | null>(null);

  const stable = points.filter((p) => p.stability_label === 'stable');
  const metastable = points.filter((p) => p.stability_label === 'metastable');
  const unstable = points.filter((p) => p.stability_label === 'unstable');
  const unknown = points.filter((p) => p.stability_label === 'unknown');

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
          <XAxis
            dataKey="formation_energy_per_atom"
            type="number"
            name="Energía de formación"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{
              value: 'Energía de formación (eV/átomo)',
              position: 'insideBottom',
              offset: -10,
              fill: '#6b7280',
              fontSize: 11,
            }}
            domain={['auto', 'auto']}
          />
          <YAxis
            dataKey="energy_above_hull"
            type="number"
            name="Energía sobre el hull"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{
              value: 'Energía sobre el hull (eV/átomo)',
              angle: -90,
              position: 'insideLeft',
              offset: 15,
              fill: '#6b7280',
              fontSize: 11,
            }}
            domain={[0, 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={0.05}
            stroke="#f59e0b"
            strokeDasharray="6 3"
            label={{ value: 'Umbral 0.05 eV/átomo', position: 'insideTopRight', fill: '#f59e0b', fontSize: 10 }}
          />
          <Legend
            wrapperStyle={{ paddingTop: 8, fontSize: 11 }}
            formatter={(value) => <span style={{ color: '#9ca3af' }}>{value}</span>}
          />
          <Scatter
            name="Estable"
            data={stable}
            fill="#10b981"
            opacity={0.8}
            isAnimationActive
            animationDuration={700}
            onClick={(d) => setSelected(d as unknown as HullPoint)}
          />
          <Scatter
            name="Metaestable"
            data={metastable}
            fill="#f59e0b"
            opacity={0.8}
            isAnimationActive
            animationDuration={900}
            onClick={(d) => setSelected(d as unknown as HullPoint)}
          />
          <Scatter
            name="Inestable"
            data={unstable}
            fill="#ef4444"
            opacity={0.7}
            isAnimationActive
            animationDuration={1100}
            onClick={(d) => setSelected(d as unknown as HullPoint)}
          />
          {unknown.length > 0 && (
            <Scatter
              name="Desconocido"
              data={unknown}
              fill="#6b7280"
              opacity={0.5}
              isAnimationActive
              animationDuration={1100}
            />
          )}
        </ScatterChart>
      </ResponsiveContainer>

      {selected && (
        <div className="absolute top-4 right-4 bg-navy-800 border border-cyan-500/40 rounded-xl p-4 text-xs shadow-2xl min-w-[180px]">
          <div className="flex items-start justify-between gap-3">
            <div className="font-mono text-cyan-400 font-bold text-sm">{selected.formula}</div>
            <button
              onClick={() => setSelected(null)}
              className="text-gray-500 hover:text-white leading-none"
            >
              ✕
            </button>
          </div>
          <div className="mt-2 space-y-1 text-gray-300">
            <div>Energía de formación: <span className="text-white">{selected.formation_energy_per_atom?.toFixed(4)}</span></div>
            <div>Energía sobre el hull: <span className="text-white">{selected.energy_above_hull?.toFixed(4)}</span></div>
          </div>
          <Link
            to={`/materials/${selected.material_id}`}
            className="mt-3 block text-center text-cyan-400 hover:text-cyan-300 text-xs border border-cyan-500/30 rounded-lg py-1 transition-colors"
          >
            Ver material →
          </Link>
        </div>
      )}

      <p className="text-xs text-gray-600 mt-2">
        Haz clic en un punto para inspeccionarlo. La línea punteada amarilla = umbral de estabilidad de 0.05 eV/átomo.
      </p>
    </div>
  );
}
