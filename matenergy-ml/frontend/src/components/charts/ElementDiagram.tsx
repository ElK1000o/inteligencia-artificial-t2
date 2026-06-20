import { ElementData } from '../../types';

interface Props {
  elements: ElementData[];
}

// Map electronegativity (0.7 – 4.0) to a CSS hsl color (blue → cyan → green → yellow → red)
function enToColor(en: number | null): string {
  if (en === null) return '#64748b';
  const t = Math.max(0, Math.min(1, (en - 0.7) / (4.0 - 0.7)));
  // blue (hsl 230) → cyan (hsl 185) → green (hsl 140) → yellow (hsl 60) → red (hsl 0)
  const hue = Math.round(230 - t * 230);
  const sat = 70 + t * 20;
  const lit = 55 - t * 10;
  return `hsl(${hue}, ${sat}%, ${lit}%)`;
}

// Scale atomic radius (0.3–2.0 Å) to SVG circle radius (18–50 px)
function radiusToSvgR(r: number | null): number {
  if (r === null) return 26;
  return 18 + ((r - 0.3) / (2.0 - 0.3)) * 32;
}

function blockLabel(block: string): string {
  const map: Record<string, string> = { s: 'alcalino/alcalinotérreo', p: 'bloque p', d: 'metal de transición', f: 'bloque f' };
  return map[block] ?? block;
}

export function ElementDiagram({ elements }: Props) {
  if (!elements || elements.length === 0) return null;

  const svgPadding = 24;
  const slotW = 120;
  const svgH = 260;
  const svgW = elements.length * slotW + svgPadding * 2;
  const midY = 120;
  const lineY = midY + 8;

  return (
    <div className="overflow-x-auto">
      {/* Legend */}
      <div className="flex items-center gap-6 mb-4 text-xs text-gray-400 flex-wrap">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: 'hsl(230,70%,55%)' }} />
          EN baja (metálico)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: 'hsl(140,80%,45%)' }} />
          EN media (metaloide)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: 'hsl(0,90%,55%)' }} />
          EN alta (no metal)
        </span>
        <span className="ml-auto text-gray-500 italic">Tamaño del círculo ∝ radio atómico</span>
      </div>

      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        width={svgW}
        height={svgH}
        className="block"
        style={{ maxWidth: '100%' }}
      >
        {/* Connecting backbone line */}
        <line
          x1={svgPadding + slotW / 2}
          y1={lineY}
          x2={svgPadding + elements.length * slotW - slotW / 2}
          y2={lineY}
          stroke="#334155"
          strokeWidth={2}
          strokeDasharray="6 3"
        />

        {elements.map((el, i) => {
          const cx = svgPadding + i * slotW + slotW / 2;
          const r = radiusToSvgR(el.atomic_radius);
          const color = enToColor(el.electronegativity);
          const oxi = el.common_oxidation_states.map((s) => (s > 0 ? `+${s}` : `${s}`)).join(', ');

          return (
            <g key={el.symbol}>
              {/* Glow ring */}
              <circle
                cx={cx}
                cy={midY}
                r={r + 6}
                fill="none"
                stroke={color}
                strokeWidth={1.5}
                opacity={0.25}
              />
              {/* Main atom circle */}
              <circle
                cx={cx}
                cy={midY}
                r={r}
                fill={color}
                opacity={0.85}
              />
              {/* Inner shimmer */}
              <circle
                cx={cx - r * 0.28}
                cy={midY - r * 0.28}
                r={r * 0.35}
                fill="white"
                opacity={0.18}
              />

              {/* Element symbol */}
              <text
                x={cx}
                y={midY + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="white"
                fontSize={r > 34 ? 18 : 14}
                fontWeight="700"
                fontFamily="monospace"
              >
                {el.symbol}
              </text>

              {/* Fraction label inside */}
              {el.fraction < 1 && (
                <text
                  x={cx}
                  y={midY + r * 0.52}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="white"
                  fontSize={9}
                  opacity={0.7}
                >
                  {(el.fraction * 100).toFixed(0)}%
                </text>
              )}

              {/* Atomic radius label above */}
              <text
                x={cx}
                y={midY - r - 12}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize={10}
              >
                {el.atomic_radius !== null ? `${el.atomic_radius.toFixed(2)} Å` : '—'}
              </text>

              {/* EN below */}
              <text
                x={cx}
                y={midY + r + 14}
                textAnchor="middle"
                fill={color}
                fontSize={11}
                fontWeight="600"
              >
                χ = {el.electronegativity?.toFixed(2) ?? '—'}
              </text>

              {/* Period / Group chip */}
              <text
                x={cx}
                y={midY + r + 28}
                textAnchor="middle"
                fill="#475569"
                fontSize={9}
              >
                fila {el.period} · grupo {el.group}
              </text>

              {/* Oxidation states */}
              <text
                x={cx}
                y={midY + r + 42}
                textAnchor="middle"
                fill="#64748b"
                fontSize={9}
              >
                {oxi || '—'}
              </text>
            </g>
          );
        })}

        {/* EN axis at bottom */}
        <g transform={`translate(${svgPadding + slotW / 2}, ${svgH - 14})`}>
          <line
            x1={0}
            y1={0}
            x2={elements.length * slotW - slotW}
            y2={0}
            stroke="#1e293b"
            strokeWidth={1}
          />
        </g>
      </svg>

      {/* Block badges */}
      <div className="flex gap-2 flex-wrap mt-2">
        {elements.map((el) => (
          <span
            key={el.symbol}
            className="text-xs px-2 py-0.5 rounded-full border"
            style={{ borderColor: enToColor(el.electronegativity), color: enToColor(el.electronegativity) }}
          >
            {el.symbol}: {blockLabel(el.block)}
          </span>
        ))}
      </div>
    </div>
  );
}
