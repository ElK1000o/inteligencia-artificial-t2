import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface FeatureImportanceItem {
  feature: string;
  importance: number;
}

interface FeatureImportanceChartProps {
  data: FeatureImportanceItem[];
  topN?: number;
  height?: number;
}

export function FeatureImportanceChart({ data, topN = 15, height = 320 }: FeatureImportanceChartProps) {
  const sliced = data.slice(0, topN);
  const max = Math.max(...sliced.map((d) => d.importance), 0.001);

  return (
    <div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={sliced}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            domain={[0, max * 1.05]}
          />
          <YAxis
            dataKey="feature"
            type="category"
            width={160}
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            tickFormatter={(v: string) => (v.length > 22 ? v.slice(0, 20) + '…' : v)}
          />
          <Tooltip
            contentStyle={{ background: '#0f2744', border: '1px solid #1e3a5f', borderRadius: 8 }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(val: number) => [val.toFixed(5), 'Importancia']}
          />
          <Bar dataKey="importance" radius={[0, 4, 4, 0]} isAnimationActive animationDuration={600}>
            {sliced.map((_, i) => {
              const t = 1 - i / sliced.length;
              const r = Math.round(6 + (16 - 6) * (1 - t));
              const g = Math.round(182 + (185 - 182) * t);
              const b = Math.round(212 + (250 - 212) * t);
              return <Cell key={i} fill={`rgb(${r},${g},${b})`} />;
            })}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-600 mt-1">
        Las {sliced.length} características más importantes (mayor valor = mayor influencia en las predicciones).
      </p>
    </div>
  );
}
