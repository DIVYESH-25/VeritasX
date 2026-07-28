import React from 'react';

interface CyberBadgeProps {
  label: string;
  variant?: 'cyan' | 'purple' | 'red' | 'emerald' | 'amber';
  pulse?: boolean;
}

export const CyberBadge: React.FC<CyberBadgeProps> = ({
  label,
  variant = 'cyan',
  pulse = true,
}) => {
  const getBadgeColors = () => {
    switch (variant) {
      case 'purple':
        return {
          bg: 'bg-purple-500/10 border-purple-500/40 text-purple-300',
          dot: 'bg-purple-400',
        };
      case 'red':
        return {
          bg: 'bg-red-500/10 border-red-500/40 text-red-300',
          dot: 'bg-red-400',
        };
      case 'emerald':
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300',
          dot: 'bg-emerald-400',
        };
      case 'amber':
        return {
          bg: 'bg-amber-500/10 border-amber-500/40 text-amber-300',
          dot: 'bg-amber-400',
        };
      case 'cyan':
      default:
        return {
          bg: 'bg-cyan-500/10 border-cyan-500/40 text-cyan-300',
          dot: 'bg-cyan-400',
        };
    }
  };

  const colors = getBadgeColors();

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-mono tracking-wider backdrop-blur-md uppercase ${colors.bg}`}
    >
      <span className="relative flex h-2 w-2">
        {pulse && (
          <span
            className={`absolute inline-flex h-full w-full animate-ping rounded-full ${colors.dot} opacity-75`}
          />
        )}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${colors.dot}`} />
      </span>
      {label}
    </span>
  );
};
