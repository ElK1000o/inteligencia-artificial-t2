import { useMemo } from 'react';
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Label,
} from 'recharts';

export interface ParetoPoint {
  material_id: string;
  formula: string;
  energy_above_hull: number;
  formation_energy_per_atom: number;
  is_pareto?: boolean;
}

function computePareto(points: ParetoPoint[]): ParetoPoint[] {
  return points.map((p, i) => {
    const dominated = points.some(
      (q, j) =>
        j !== i &&
        q.energy_above_hull <= p.energy_above_hull &&
        q.formation_energy_per_atom <= p.formation_energy_per_atom &&
        (q.energy_above_hull < p.energy_above_hull || q.formation_energy_per_atom < p.formation_energy_per_atom)
    );
    return { ...p, is_pareto: !dominated };
  });
}

interface ParetoPlotProps {
  points: ParetoPoint[];
  height?: number;
}

export function ParetoPlot({ points, height = 380 }: ParetoPlotProps) {
  const annotated = useMemo(() => computePareto(points), [points]);
  const paretoPoints = annotated.filter((p) => p.is_pareto).sort((a, b) => a.energy_above_hull - b.energy_above_hull);
  const nonPareto = annotated.filter((p) => !p.is_pareto);
  const nPareto = paretoPoints.length;

  const paretoLine = paretoPoints.map((p) => ({
    x: p.energy_above_hull,
    y: p.formation_energy_per_atom,
  }));

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <div className="bg-amber-500/20 border border-amber-500/30 rounded-lg px-3 py-2 text-xs text-center">
          <div className="text-amber-400 font-bold text-lg">{nPareto}</div>
          <div className="text-gray-500">Candidatos Pareto-óptimos</div>
        </div>
        <p className="text-xs text-gray-500 flex-1">
          Los materiales Pareto-óptimos no están dominados en ningún eje — representan el mejor
          equilibrio entre baja energía sobre el hull (estabilidad) y energía de formación negativa
          (favorabilidad termodinámica). Son los principales candidatos para síntesis.
        </p>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart margin={{ top: 20, right: 30, left: 10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
          <XAxis
            dataKey="x"
            type="number"
            name="Energía sobre el hull"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            domain={['auto', 'auto']}
          >
            <Label value="Energía sobre el hull (eV/átomo)" offset={-10} position="insideBottom" fill="#6b7280" fontSize={11} />
          </XAxis>
          <YAxis
            dataKey="y"
            type="number"
            name="Energía de formación"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            domain={['auto', 'auto']}
          >
            <Label value="Energía de formación (eV/átomo)" angle={-90} position="insideLeft" offset={15} fill="#6b7280" fontSize={11} />
          </YAxis>
          <Tooltip
            contentStyle={{ background: '#0f2744', border: '1px solid #1e3a5f', borderRadius: 8 }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as ParetoPoint;
              return (
                <div className="bg-navy-800 border border-navy-500 rounded-lg px-3 py-2 text-xs shadow-xl">
                  <div className="font-mono text-cyan-400 font-semibold">{d.formula ?? '—'}</div>
                  {d.is_pareto && (
                    <div className="text-amber-400 text-xs font-medium">★ Pareto-óptimo</div>
                  )}
                  <div className="text-gray-300 mt-1">
                    Energía sobre el hull: <span className="text-white">{d.energy_above_hull?.toFixed(4)}</span>
                  </div>
                  <div className="text-gray-300">
                    Energía de formación: <span className="text-white">{d.formation_energy_per_atom?.toFixed(4)}</span>
                  </div>
                </div>
              );
            }}
          />
          <Scatter
            data={nonPareto.map((p) => ({ ...p, x: p.energy_above_hull, y: p.formation_energy_per_atom }))}
            fill="#4b5563"
            opacity={0.6}
            isAnimationActive
            animationDuration={800}
            name="No Pareto"
          />
          <Scatter
            data={paretoPoints.map((p) => ({ ...p, x: p.energy_above_hull, y: p.formation_energy_per_atom }))}
            fill="#f59e0b"
            opacity={0.9}
            isAnimationActive
            animationDuration={600}
            name="Pareto-óptimo"
          >
            {paretoPoints.map((_, i) => (
              <Cell key={i} fill="#f59e0b" r={7} />
            ))}
          </Scatter>
          <Line
            data={paretoLine}
            dataKey="y"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            isAnimationActive
            animationDuration={1000}
            name="Frontera de Pareto"
          />
        </ComposedChart>
      </ResponsiveContainer>

      {paretoPoints.length > 0 && (
        <div className="mt-3">
          <div className="text-xs text-gray-500 mb-2">Principales candidatos Pareto:</div>
          <div className="flex flex-wrap gap-2">
            {paretoPoints.slice(0, 8).map((p) => (
              <span
                key={p.material_id}
                className="px-2 py-1 bg-amber-500/20 border border-amber-500/30 rounded text-xs font-mono text-amber-400"
              >
                {p.formula}
              </span>
            ))}
            {paretoPoints.length > 8 && (
              <span className="text-xs text-gray-600 self-center">+{paretoPoints.length - 8} más</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
