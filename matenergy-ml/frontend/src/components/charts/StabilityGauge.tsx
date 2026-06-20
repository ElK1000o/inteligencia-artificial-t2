interface StabilityGaugeProps {
  energyAboveHull: number | null;
  size?: number;
}

const MAX_EAH = 0.3;

export function StabilityGauge({ energyAboveHull, size = 48 }: StabilityGaugeProps) {
  const eah = energyAboveHull;
  const t = eah !== null ? Math.min(eah / MAX_EAH, 1) : null;

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const strokeW = size * 0.12;

  // semi-circle arc (180°): start at left (180°), end at right (0°)
  const startAngle = Math.PI;
  const endAngle = 0;

  const arcPath = (from: number, to: number) => {
    const x1 = cx + r * Math.cos(from);
    const y1 = cy - r * Math.sin(from);
    const x2 = cx + r * Math.cos(to);
    const y2 = cy - r * Math.sin(to);
    const large = Math.abs(to - from) > Math.PI ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  };

  const fillAngle = t !== null ? startAngle - t * Math.PI : null;
  const color = eah === null ? '#6b7280' : eah <= 0.05 ? '#10b981' : eah <= 0.1 ? '#f59e0b' : '#ef4444';

  return (
    <svg width={size} height={size / 2 + 2} viewBox={`0 0 ${size} ${size / 2 + 4}`} aria-hidden>
      {/* Background track */}
      <path
        d={arcPath(startAngle, endAngle)}
        fill="none"
        stroke="#1e3a5f"
        strokeWidth={strokeW}
        strokeLinecap="round"
      />
      {/* Colored fill */}
      {fillAngle !== null && (
        <path
          d={arcPath(startAngle, fillAngle)}
          fill="none"
          stroke={color}
          strokeWidth={strokeW}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
        />
      )}
    </svg>
  );
}
