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
    <section className="relative min-h-screen w-full flex items-center justify-center bg-[#020617] overflow-hidden px-4">
      {/* Full-Screen 3D Slow Moving Particles + Large Center Cyan/Blue Radial Glow */}
      <NeuralCoreScene />

      {/* Screen Center: Welcome to VeritasX Heading + Glass Black REVEAL THE TRUTH Button */}
      <div className="relative z-10 text-center pointer-events-auto space-y-6 max-w-4xl mx-auto w-full flex flex-col items-center justify-center">
        {/* Welcome to VeritasX Heading */}
        <motion.h1
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="font-orbitron text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-wider text-slate-100"
        >
          Welcome to <span className="text-[#00E5FF] glow-cyan-text">VeritasX</span>
        </motion.h1>

        {/* REVEAL THE TRUTH Button - Perfectly Balanced Cyan Glowing Box */}
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.2, ease: 'easeOut' }}
          className="relative inline-block group"
        >
          {/* Ambient Cyan Glow Aura */}
          <div className="absolute -inset-1 rounded-md bg-[#00E5FF] opacity-55 blur-lg group-hover:opacity-85 group-hover:blur-xl transition-all duration-300 pointer-events-none" />

          <CyberButton
            variant="primary"
            size="lg"
            onClick={onEnterToFind}
            cursorLabel="REVEAL_TRUTH"
            className="relative z-10 text-lg sm:text-2xl px-10 py-5 rounded-md bg-black/35 backdrop-blur-xl border-2 border-[#00E5FF]/90 text-[#00E5FF] shadow-[0_0_30px_rgba(0,229,255,0.55),inset_0_0_15px_rgba(0,229,255,0.25)] group-hover:text-white group-hover:bg-[#00E5FF]/20 group-hover:border-[#00E5FF] group-hover:shadow-[0_0_50px_rgba(0,229,255,0.85),inset_0_0_25px_rgba(0,229,255,0.4)] transition-all duration-300 tracking-widest font-orbitron font-bold uppercase"
          >
            REVEAL THE TRUTH
          </CyberButton>
        </motion.div>
      </div>
    </section>
  );
};
