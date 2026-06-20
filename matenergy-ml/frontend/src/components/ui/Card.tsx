import { ReactNode } from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  badge?: string;
  badgeColor?: 'cyan' | 'green' | 'yellow' | 'red';
}

const badgeColors = {
  cyan: 'bg-cyan-500/20 text-cyan-400',
  green: 'bg-green-500/20 text-green-400',
  yellow: 'bg-yellow-500/20 text-yellow-400',
  red: 'bg-red-500/20 text-red-400',
};

export function Card({
  title,
  subtitle,
  children,
  className = '',
  badge,
  badgeColor = 'cyan',
}: CardProps) {
  return (
    <div className={`bg-navy-800 border border-navy-600 rounded-xl p-6 ${className}`}>
      {(title || badge) && (
        <div className="flex items-center justify-between mb-4">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
                {title}
              </h3>
            )}
            {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
          </div>
          {badge && (
            <span
              className={`text-xs px-2 py-1 rounded-full font-medium ${badgeColors[badgeColor]}`}
            >
              {badge}
            </span>
          )}
        </div>
      )}
      {children}
    </div>
  );
}
