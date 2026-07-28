import React, { ReactNode } from 'react';
import { useCursorState } from '@/hooks/useCursorState';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glow?: 'cyan' | 'purple' | 'none';
  interactive?: boolean;
  cursorLabel?: string;
  onClick?: () => void;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  glow = 'cyan',
  interactive = false,
  cursorLabel = 'INSPECT',
  onClick,
}) => {
  const { setCursor, resetCursor } = useCursorState();

  const getGlowStyles = () => {
    switch (glow) {
      case 'cyan':
        return 'border-cyan-500/20 hover:border-cyan-400/50 hover:shadow-[0_0_30px_rgba(0,243,255,0.15)]';
      case 'purple':
        return 'border-purple-500/20 hover:border-purple-400/50 hover:shadow-[0_0_30px_rgba(157,78,221,0.15)]';
      case 'none':
      default:
        return 'border-slate-800';
    }
  };

  return (
    <div
      onClick={onClick}
      onMouseEnter={() => interactive && setCursor('card', cursorLabel)}
      onMouseLeave={() => interactive && resetCursor()}
      className={`cyber-glass cyber-corner-box relative rounded-lg border p-6 transition-all duration-300 ${getGlowStyles()} ${
        interactive ? 'cursor-none hover:-translate-y-1' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};
