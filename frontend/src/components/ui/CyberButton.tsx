import React, { ReactNode } from 'react';
import { useCursorState } from '@/hooks/useCursorState';
import { motion } from 'framer-motion';

interface CyberButtonProps {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  icon?: ReactNode;
  className?: string;
  cursorLabel?: string;
}

export const CyberButton: React.FC<CyberButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  icon,
  className = '',
  cursorLabel = 'SELECT',
}) => {
  const { setCursor, resetCursor } = useCursorState();

  const getVariantStyles = () => {
    switch (variant) {
      case 'primary':
        return 'bg-cyan-500/10 text-cyan-300 border border-cyan-400/50 shadow-[0_0_20px_rgba(0,243,255,0.2)] hover:bg-cyan-400 hover:text-black hover:border-cyan-300 hover:shadow-[0_0_30px_rgba(0,243,255,0.6)]';
      case 'secondary':
        return 'bg-purple-600/15 text-purple-300 border border-purple-500/40 shadow-[0_0_20px_rgba(157,78,221,0.2)] hover:bg-purple-600 hover:text-white hover:border-purple-400 hover:shadow-[0_0_30px_rgba(157,78,221,0.6)]';
      case 'outline':
        return 'bg-slate-900/40 text-slate-200 border border-slate-700/80 hover:border-cyan-400/60 hover:text-cyan-300 hover:shadow-[0_0_15px_rgba(0,243,255,0.3)]';
      case 'danger':
        return 'bg-red-500/10 text-red-400 border border-red-500/50 hover:bg-red-500 hover:text-white hover:shadow-[0_0_25px_rgba(239,68,68,0.5)]';
      default:
        return '';
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return 'px-3.5 py-1.5 text-xs font-mono tracking-wider';
      case 'lg':
        return 'px-7 py-3.5 text-base font-space tracking-wide';
      case 'md':
      default:
        return 'px-5 py-2.5 text-sm font-space tracking-wider';
    }
  };

  return (
    <motion.button
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      onMouseEnter={() => setCursor('button', cursorLabel)}
      onMouseLeave={resetCursor}
      className={`group relative inline-flex items-center justify-center font-semibold transition-all duration-300 rounded-sm uppercase ${getVariantStyles()} ${getSizeStyles()} ${className}`}
    >
      {/* Corner Bracket Details */}
      <span className="absolute -top-[1px] -left-[1px] w-1.5 h-1.5 border-t border-l border-cyan-400 transition-all group-hover:w-2.5 group-hover:h-2.5" />
      <span className="absolute -bottom-[1px] -right-[1px] w-1.5 h-1.5 border-b border-r border-cyan-400 transition-all group-hover:w-2.5 group-hover:h-2.5" />

      {icon && <span className="mr-2 transition-transform duration-300 group-hover:scale-110">{icon}</span>}
      <span>{children}</span>
    </motion.button>
  );
};
