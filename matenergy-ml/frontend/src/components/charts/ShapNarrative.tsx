import { ShieldCheck, TrendingUp, TrendingDown, AlertTriangle, Info, Minus, type LucideIcon } from 'lucide-react';
import type { ShapNarrativeData, NarrativeFactor } from '../../utils/shapNarrative';

interface Props {
  data: ShapNarrativeData;
}

const VERDICT_STYLES = {
  positive: {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    Icon: ShieldCheck,
  },
  warning: {
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    Icon: AlertTriangle,
  },
  negative: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    Icon: TrendingDown,
  },
  neutral: {
    bg: 'bg-gray-500/10',
    border: 'border-gray-500/30',
    text: 'text-gray-400',
    Icon: Minus,
  },
};

function FactorList({
  label,
  factors,
  contributionColor,
  HeaderIcon,
}: {
  label: string;
  factors: NarrativeFactor[];
  contributionColor: string;
  HeaderIcon: LucideIcon;
}) {
  if (factors.length === 0) return null;
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <HeaderIcon size={12} className={contributionColor} />
        <span className="text-xs font-semibold text-gray-400">{label}</span>
      </div>
      <ul className="space-y-1.5">
        {factors.map((f, i) => (
          <li
            key={i}
            className="flex items-start justify-between gap-2 bg-navy-700 rounded-lg px-2.5 py-1.5"
          >
            <span className="text-xs text-gray-300 leading-tight">{f.label}</span>
            <div className="text-right shrink-0 ml-2">
              <span className="text-xs font-mono text-gray-500 block">{f.featureValue}</span>
              <span className={`text-xs font-mono ${contributionColor}`}>
                {f.shapContribution}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ShapNarrative({ data }: Props) {
  const style = VERDICT_STYLES[data.verdictLevel];
  const { Icon: VerdictIcon } = style;

  // Color convention:
  // For lowerIsBetter (e.g. EAH): pushing UP is bad → red, pushing DOWN is good → green
  // For !lowerIsBetter (e.g. band_gap, is_stable): pushing UP is good → green, pushing DOWN is bad → red
  const upColor = data.lowerIsBetter ? 'text-red-400' : 'text-emerald-400';
  const downColor = data.lowerIsBetter ? 'text-emerald-400' : 'text-red-400';
  const UpIcon = data.lowerIsBetter ? TrendingUp : TrendingUp;
  const DownIcon = data.lowerIsBetter ? TrendingDown : TrendingDown;

  const hasBothSections = data.pushingUpFactors.length > 0 && data.pushingDownFactors.length > 0;

  return (
    <div className="space-y-4 mt-5 pt-5 border-t border-navy-600">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        Narrativa Automática
      </p>

      {/* Headline verdict */}
      <div className={`flex items-start gap-3 p-3 rounded-lg border ${style.bg} ${style.border}`}>
        <VerdictIcon size={16} className={`${style.text} mt-0.5 shrink-0`} />
        <p className={`text-sm font-medium leading-snug ${style.text}`}>{data.headline}</p>
      </div>

      {/* Factor columns */}
      <div className={`grid gap-4 ${hasBothSections ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1'}`}>
        <FactorList
          label={data.pushingUpLabel}
          factors={data.pushingUpFactors}
          contributionColor={upColor}
          HeaderIcon={UpIcon}
        />
        <FactorList
          label={data.pushingDownLabel}
          factors={data.pushingDownFactors}
          contributionColor={downColor}
          HeaderIcon={DownIcon}
        />
      </div>

      {/* Baseline note */}
      <p className="text-xs text-gray-600 font-mono">{data.baselineNote}</p>

      {/* Scientific context */}
      <div className="flex items-start gap-2 p-3 bg-navy-700/50 rounded-lg border border-navy-600">
        <Info size={12} className="text-cyan-500/70 mt-0.5 shrink-0" />
        <p className="text-xs text-gray-500 leading-relaxed">{data.scientificContext}</p>
      </div>
    </div>
  );
}
