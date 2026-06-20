import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

export interface SpaceMapPoint {
  material_id: string;
  formula: string;
  x: number;
  y: number;
  z: number | null;
  color_value: number | null;
  color_property: string;
}

interface ChemicalSpaceMapProps {
  points: SpaceMapPoint[];
  colorMin: number;
  colorMax: number;
  colorProperty: string;
  height?: number;
}

function valueToColor(val: number | null, min: number, max: number): string {
  if (val === null) return '#6b7280';
  const t = Math.max(0, Math.min(1, (val - min) / (max - min || 1)));
  // blue (low) → cyan → green → yellow → red (high)
  if (t < 0.25) {
    const s = t / 0.25;
    return `rgb(${Math.round(59 + (6 - 59) * s)},${Math.round(130 + (182 - 130) * s)},${Math.round(246 - (246 - 212) * s)})`;
  }
  if (t < 0.5) {
    const s = (t - 0.25) / 0.25;
    return `rgb(${Math.round(6 + (16 - 6) * s)},${Math.round(182 - (182 - 185) * s)},${Math.round(212 - 212 * s)})`;
  }
  if (t < 0.75) {
    const s = (t - 0.5) / 0.25;
    return `rgb(${Math.round(16 + (245 - 16) * s)},${Math.round(185 - (185 - 158) * s)},0)`;
  }
  const s = (t - 0.75) / 0.25;
  return `rgb(${Math.round(245 + (239 - 245) * s)},${Math.round(158 - 158 * s)},${Math.round(68 * s)})`;
}

export function ChemicalSpaceMap({ points, colorMin, colorMax, colorProperty, height = 400 }: ChemicalSpaceMapProps) {
  const [selected, setSelected] = useState<SpaceMapPoint | null>(null);

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 15, right: 30, left: 10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
          <XAxis
            dataKey="x"
            type="number"
            name="t-SNE 1"
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            label={{ value: 'Dimensión t-SNE 1', position: 'insideBottom', offset: -10, fill: '#6b7280', fontSize: 11 }}
            domain={['auto', 'auto']}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="t-SNE 2"
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            label={{ value: 'Dimensión t-SNE 2', angle: -90, position: 'insideLeft', offset: 15, fill: '#6b7280', fontSize: 11 }}
            domain={['auto', 'auto']}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as SpaceMapPoint;
              return (
                <div className="bg-navy-800 border border-navy-500 rounded-lg px-3 py-2 text-xs shadow-xl">
                  <div className="font-mono text-cyan-400 font-semibold">{d.formula}</div>
                  <div className="text-gray-300 mt-1">
                    {colorProperty}:{' '}
                    <span className="text-white">
                      {d.color_value !== null ? d.color_value.toFixed(4) : '—'}
                    </span>
                  </div>
                </div>
              );
            }}
          />
          <Scatter
            data={points}
            isAnimationActive
            animationDuration={900}
            onClick={(d) => setSelected(d as unknown as SpaceMapPoint)}
          >
            {points.map((p, i) => (
              <Cell
                key={i}
                fill={valueToColor(p.color_value, colorMin, colorMax)}
                opacity={0.8}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Color legend */}
      <div className="flex items-center gap-2 mt-2 px-2">
        <span className="text-xs text-gray-500">{colorMin.toFixed(3)}</span>
        <div
          className="flex-1 h-2.5 rounded-full"
          style={{
            background: 'linear-gradient(to right, rgb(59,130,246), rgb(6,182,212), rgb(16,185,0), rgb(245,158,0), rgb(239,68,68))',
          }}
        />
        <span className="text-xs text-gray-500">{colorMax.toFixed(3)}</span>
        <span className="text-xs text-gray-600 ml-1">({colorProperty})</span>
      </div>

      {selected && (
        <div className="absolute top-4 right-4 bg-navy-800 border border-cyan-500/40 rounded-xl p-4 text-xs shadow-2xl min-w-[180px]">
          <div className="flex items-start justify-between gap-3">
            <div className="font-mono text-cyan-400 font-bold">{selected.formula}</div>
            <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white leading-none">✕</button>
          </div>
          <div className="text-gray-300 mt-1">
            {colorProperty}: <span className="text-white">{selected.color_value?.toFixed(4) ?? '—'}</span>
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
        Cada punto es un material proyectado desde {'>'}130 dimensiones de descriptores a 2D mediante t-SNE.
        Los materiales similares se agrupan juntos. Haz clic en un punto para inspeccionarlo.
      </p>
    </div>
  );
}
