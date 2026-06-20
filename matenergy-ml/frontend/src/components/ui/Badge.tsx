type BadgeVariant =
  | 'stable'
  | 'unstable'
  | 'pending'
  | 'valid'
  | 'invalid'
  | 'high'
  | 'moderate'
  | 'low'
  | 'default';

const variants: Record<BadgeVariant, string> = {
  stable: 'bg-green-500/20 text-green-400 border border-green-500/30',
  unstable: 'bg-red-500/20 text-red-400 border border-red-500/30',
  pending: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  valid: 'bg-green-500/20 text-green-400 border border-green-500/30',
  invalid: 'bg-red-500/20 text-red-400 border border-red-500/30',
  high: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  moderate: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  low: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
  default: 'bg-navy-600 text-gray-300 border border-navy-500',
};

export function Badge({
  label,
  variant = 'default',
}: {
  label: string;
  variant?: BadgeVariant;
}) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]}`}
    >
      {label}
    </span>
  );
}
