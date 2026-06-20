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
} from 'recharts';

interface ParityPoint {
  actual: number;
  predicted: number;
  absError: number;
}

interface ParityPlotProps {
  yTest: number[];
  yPred: number[];
  mae: number;
  r2: number;
  targetProperty: string;
}

function lerpColor(t: number): string {
  // green → yellow → red based on t in [0,1]
  if (t < 0.5) {
    const r = Math.round(16 + (245 - 16) * t * 2);
    const g = Math.round(185 - (185 - 159) * t * 2);
    return `rgb(${r},${g},0)`;
  }
  const r = 239;
  const g = Math.round(68 - 68 * (t - 0.5) * 2);
  return `rgb(${r},${g},68)`;
}

export function ParityPlot({ yTest, yPred, mae, r2, targetProperty }: ParityPlotProps) {
  const points: ParityPoint[] = yTest.map((actual, i) => ({
    actual,
    predicted: yPred[i],
    absError: Math.abs(yPred[i] - actual),
  }));

  const maxError = Math.max(...points.map((p) => p.absError), 0.001);
  const allVals = [...yTest, ...yPred];
  const minVal = Math.min(...allVals);
  const maxVal = Math.max(...allVals);
  const padding = (maxVal - minVal) * 0.08;
  const axiMin = minVal - padding;
  const axiMax = maxVal + padding;

  const perfectLine = [
    { actual: axiMin, predicted: axiMin },
    { actual: axiMax, predicted: axiMax },
  ];

  return (
    <div>
      <div className="flex gap-6 mb-4">
        <div className="bg-navy-700 rounded-lg px-4 py-2.5 text-center">
          <div className="text-lg font-bold font-mono text-cyan-400">{mae.toFixed(4)}</div>
          <div className="text-xs text-gray-500 mt-0.5 uppercase">MAE</div>
        </div>
        <div className="bg-navy-700 rounded-lg px-4 py-2.5 text-center">
          <div className="text-lg font-bold font-mono text-cyan-400">{r2.toFixed(4)}</div>
          <div className="text-xs text-gray-500 mt-0.5 uppercase">R²</div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart margin={{ top: 15, right: 20, left: 10, bottom: 40 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
          <XAxis
            dataKey="actual"
            type="number"
            name="DFT (real)"
            domain={[axiMin, axiMax]}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: 'DFT (real)', position: 'insideBottom', offset: -10, fill: '#6b7280', fontSize: 11 }}
          />
          <YAxis
            dataKey="predicted"
            type="number"
            name="ML (predicho)"
            domain={[axiMin, axiMax]}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            label={{ value: 'ML (predicho)', angle: -90, position: 'insideLeft', offset: 15, fill: '#6b7280', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ background: '#0f2744', border: '1px solid #1e3a5f', borderRadius: 8 }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(val: number, name: string) => [val.toFixed(5), name]}
          />
          <Line
            data={perfectLine}
            dataKey="predicted"
            stroke="#6b7280"
            strokeDasharray="5 3"
            dot={false}
            activeDot={false}
            isAnimationActive={false}
            name="Ajuste perfecto"
          />
          <Scatter
            data={points}
            dataKey="predicted"
            isAnimationActive
            animationDuration={800}
            name={targetProperty}
          >
            {points.map((p, i) => (
              <Cell key={i} fill={lerpColor(Math.min(p.absError / maxError, 1))} opacity={0.8} />
            ))}
          </Scatter>
        </ComposedChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
        <span className="w-3 h-3 rounded-full bg-green-500 inline-block" />
        <span>Error bajo</span>
        <span className="w-3 h-3 rounded-full bg-yellow-500 inline-block ml-2" />
        <span>Medio</span>
        <span className="w-3 h-3 rounded-full bg-red-500 inline-block ml-2" />
        <span>Error alto</span>
        <span className="ml-2">— Línea punteada = ajuste perfecto</span>
      </div>
    </div>
  );
}
