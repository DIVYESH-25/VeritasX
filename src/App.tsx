import React, { useState } from 'react';
import { CursorProvider } from '@/hooks/useCursorState';
import { useLenis } from '@/hooks/useLenis';
import { CyberCursor } from '@/components/cursor/CyberCursor';
import { HeroSection } from '@/components/sections/HeroSection';
import { BatchDetectionWorkspace } from '@/components/sections/BatchDetectionWorkspace';

const AppContent: React.FC = () => {
  useLenis();
  const [currentView, setCurrentView] = useState<'portal' | 'workspace'>('portal');

  const handleEnterToFind = () => {
    setCurrentView('workspace');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBackToHero = () => {
    setCurrentView('portal');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="relative min-h-screen bg-[#030712] text-slate-100 font-inter overflow-hidden">
      {/* Custom Cyber Reticle Cursor */}
      <CyberCursor />

      <main className="min-h-screen w-full flex flex-col justify-center items-center">
        {currentView === 'portal' ? (
          /* Page 1: Pure Centered Welcome to VeritasX & ENTER TO FIND */
          <HeroSection onEnterToFind={handleEnterToFind} />
        ) : (
          /* Page 2: Pure Centered UPLOAD AN IMAGE */
          <BatchDetectionWorkspace onBackToHero={handleBackToHero} />
        )}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <CursorProvider>
      <AppContent />
    </CursorProvider>
  );
};

export default App;
