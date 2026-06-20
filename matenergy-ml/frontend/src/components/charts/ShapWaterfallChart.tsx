import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';

export interface ShapContribution {
  feature: string;
  shap_value: number;
  feature_value: number;
}

interface ShapWaterfallChartProps {
  formula: string;
  targetProperty: string;
  baseValue: number;
  predictedValue: number;
  contributions: ShapContribution[];
  topN?: number;
}

export function ShapWaterfallChart({
  formula,
  targetProperty,
  baseValue,
  predictedValue,
  contributions,
  topN = 15,
}: ShapWaterfallChartProps) {
  const top = contributions.slice(0, topN);

  const formatFeature = (name: string) =>
    name.length > 28 ? name.slice(0, 26) + '…' : name;

  return (
    <div>
      <div className="flex flex-wrap gap-3 mb-4 text-xs">
        <div className="bg-navy-700 rounded-lg px-3 py-2">
          <div className="text-gray-500">Fórmula</div>
          <div className="font-mono text-cyan-400 font-bold">{formula}</div>
        </div>
        <div className="bg-navy-700 rounded-lg px-3 py-2">
          <div className="text-gray-500">Línea base (salida promedio del modelo)</div>
          <div className="font-mono text-white">{baseValue.toFixed(4)}</div>
        </div>
        <div className="bg-navy-700 rounded-lg px-3 py-2">
          <div className="text-gray-500">{targetProperty} predicho</div>
          <div className="font-mono text-cyan-400 font-bold">{predictedValue.toFixed(4)}</div>
        </div>
      </div>

      <p className="text-xs text-gray-500 mb-3">
        Las barras muestran cómo cada característica atómica empuja la predicción por encima (positivo, verde) o por debajo
        (negativo, rojo) de la línea base del modelo. Las {topN} características principales según su contribución absoluta.
      </p>

      <ResponsiveContainer width="100%" height={Math.max(280, top.length * 22)}>
        <BarChart
          data={top}
          layout="vertical"
          margin={{ top: 5, right: 60, left: 10, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" horizontal={false} />
          <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 10 }} />
          <YAxis
            dataKey="feature"
            type="category"
            width={200}
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            tickFormatter={formatFeature}
          />
          <Tooltip
            contentStyle={{ background: '#0f2744', border: '1px solid #1e3a5f', borderRadius: 8 }}
            labelStyle={{ color: '#e2e8f0' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload as ShapContribution;
              return (
                <div className="bg-navy-800 border border-navy-500 rounded-lg p-3 text-xs">
                  <div className="text-gray-300 font-medium mb-1">{d.feature}</div>
                  <div className="text-gray-400">Valor de la característica: <span className="text-white">{d.feature_value.toFixed(4)}</span></div>
                  <div className="text-gray-400">
                    Contribución SHAP:{' '}
                    <span className={d.shap_value >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                      {d.shap_value >= 0 ? '+' : ''}{d.shap_value.toFixed(5)}
                    </span>
                  </div>
                </div>
              );
            }}
          />
          <ReferenceLine x={0} stroke="#374151" strokeWidth={1.5} />
          <Bar dataKey="shap_value" radius={[0, 4, 4, 0]} isAnimationActive animationDuration={700}>
            {top.map((d, i) => (
              <Cell key={i} fill={d.shap_value >= 0 ? '#10b981' : '#ef4444'} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
