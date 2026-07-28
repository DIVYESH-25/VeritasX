import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { CyberButton } from '@/components/ui/CyberButton';
import { NeuralCoreScene } from '@/components/3d/NeuralCoreScene';
import { useCursorState } from '@/hooks/useCursorState';

interface HeroSectionProps {
  onEnterToFind: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onEnterToFind }) => {
  const { setCursor, resetCursor } = useCursorState();

  return (
    <section className="relative min-h-screen w-full flex items-center justify-center bg-[#020617] overflow-hidden">
      {/* Full-Screen 3D Slow Moving Particles + Large Center Cyan/Blue Radial Glow */}
      <NeuralCoreScene />

      {/* Screen Center: Welcome to VeritasX Heading + Glass Black REVEAL THE TRUTH Button */}
      <div className="relative z-10 text-center pointer-events-auto space-y-6">
        {/* Welcome to VeritasX Heading */}
        <motion.h1
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="font-orbitron text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-wider text-slate-100"
        >
          Welcome to <span className="text-[#00E5FF] glow-cyan-text">VeritasX</span>
        </motion.h1>

        {/* REVEAL THE TRUTH Button - Glass Black 20% Transparency & #00E5FF Glow Border */}
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
          className="relative group inline-block"
        >
          {/* Ambient Glow Aura behind button */}
          <div className="absolute -inset-1 rounded-lg bg-gradient-to-r from-[#00E5FF] to-[#0077FF] opacity-50 blur-xl group-hover:opacity-90 transition-all duration-500" />

          <CyberButton
            variant="primary"
            size="lg"
            onClick={onEnterToFind}
            cursorLabel="REVEAL_TRUTH"
            className="relative text-lg sm:text-2xl px-10 py-5 rounded-md bg-black/20 backdrop-blur-xl border border-[#00E5FF]/80 text-[#00E5FF] shadow-[0_0_30px_rgba(0,229,255,0.5)] group-hover:text-white group-hover:border-[#00E5FF] group-hover:shadow-[0_0_60px_rgba(0,229,255,0.9)] transition-all duration-300 tracking-widest font-orbitron font-bold uppercase"
          >
            REVEAL THE TRUTH
          </CyberButton>
        </motion.div>
      </div>
    </section>
  );
};
