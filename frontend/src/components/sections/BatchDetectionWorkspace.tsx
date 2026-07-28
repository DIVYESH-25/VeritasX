import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Scan, ArrowLeft, AlertTriangle, CheckCircle, Sparkles, X, ShieldCheck } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useCursorState } from '@/hooks/useCursorState';

export interface UploadedMediaItem {
  id: string;
  name: string;
  url: string;
  isAi: boolean;
  aiProb: number;
  realProb: number;
  isScanning: boolean;
  progress: number;
}

interface BatchDetectionWorkspaceProps {
  onBackToHero: () => void;
}

export const BatchDetectionWorkspace: React.FC<BatchDetectionWorkspaceProps> = ({ onBackToHero }) => {
  const { setCursor, resetCursor } = useCursorState();
  const [items, setItems] = useState<UploadedMediaItem[]>([]);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  // Process uploaded files (Max 5 limit)
  const processFiles = (fileList: FileList | File[]) => {
    const files = Array.from(fileList).slice(0, 5);
    if (!files.length) return;

    const newItems: UploadedMediaItem[] = files.map((file, i) => {
      const isAi = Math.random() > 0.4;
      return {
        id: `uploaded-${Date.now()}-${i}`,
        name: file.name,
        url: URL.createObjectURL(file),
        isAi,
        aiProb: isAi ? Number((92 + Math.random() * 7.5).toFixed(1)) : Number((0.8 + Math.random() * 2.5).toFixed(1)),
        realProb: isAi ? Number((0.5 + Math.random() * 3).toFixed(1)) : Number((95 + Math.random() * 4.5).toFixed(1)),
        isScanning: true,
        progress: 0,
      };
    });

    setItems((prev) => [...prev, ...newItems]);

    // Simulate scanning beam animation for uploaded items
    newItems.forEach((item) => {
      let p = 0;
      const interval = setInterval(() => {
        p += 25;
        if (p <= 100) {
          setItems((prev) =>
            prev.map((it) => (it.id === item.id ? { ...it, progress: p } : it))
          );
        } else {
          clearInterval(interval);
          setItems((prev) =>
            prev.map((it) => (it.id === item.id ? { ...it, isScanning: false, progress: 100 } : it))
          );
        }
      }, 300);
    });
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      processFiles(e.target.files);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      processFiles(e.dataTransfer.files);
    }
  };

  const removeItem = (id: string) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
  };

  return (
    <div className="min-h-screen w-full bg-[#020617] pt-20 pb-16 px-4 flex flex-col justify-between relative overflow-hidden">
      {/* Large Center Radial Gradient Glow: Cyan/Blue */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] center-radial-glow rounded-full blur-[110px] pointer-events-none" />

      {/* Top Controls */}
      <div className="relative z-10 max-w-6xl mx-auto w-full flex items-center justify-between">
        <button
          onClick={onBackToHero}
          onMouseEnter={() => setCursor('button')}
          onMouseLeave={resetCursor}
          className="flex items-center gap-2 px-4 py-2 rounded bg-black/20 backdrop-blur-xl border border-[#00E5FF]/60 text-xs font-mono text-[#00E5FF] shadow-[0_0_15px_rgba(0,229,255,0.3)] hover:border-[#00E5FF] hover:shadow-[0_0_25px_rgba(0,229,255,0.6)] transition-all cursor-none"
        >
          <ArrowLeft className="w-4 h-4 text-[#00E5FF]" /> [ BACK ]
        </button>

        {items.length > 0 && (
          <button
            onClick={() => setItems([])}
            onMouseEnter={() => setCursor('button')}
            onMouseLeave={resetCursor}
            className="text-xs font-mono text-slate-400 hover:text-red-400 transition-colors cursor-none"
          >
            [ CLEAR ALL ]
          </button>
        )}
      </div>

      {/* Center: UPLOAD AN IMAGE Drag & Drop Zone (Glass Black 20% Transparency & #00E5FF Glow Border) */}
      <div className="relative z-10 max-w-4xl mx-auto w-full my-auto py-8">
        <input
          type="file"
          multiple
          accept="image/*"
          id="local-image-upload"
          onChange={handleFileSelect}
          className="hidden"
        />

        <label
          htmlFor="local-image-upload"
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onMouseEnter={() => setCursor('image')}
          onMouseLeave={resetCursor}
          className={`flex flex-col items-center justify-center p-12 sm:p-16 rounded-xl border-2 border-dashed backdrop-blur-xl transition-all duration-300 cursor-none relative overflow-hidden group ${
            isDragOver
              ? 'bg-black/40 border-[#00E5FF] shadow-[0_0_50px_rgba(0,229,255,0.6)] scale-105'
              : 'bg-black/20 border-[#00E5FF]/60 hover:border-[#00E5FF] hover:bg-black/30 shadow-[0_0_30px_rgba(0,229,255,0.3)] hover:shadow-[0_0_50px_rgba(0,229,255,0.7)]'
          }`}
        >
          {/* Corner Ticks */}
          <div className="absolute top-2 left-2 w-4 h-4 border-t-2 border-l-2 border-[#00E5FF]" />
          <div className="absolute top-2 right-2 w-4 h-4 border-t-2 border-r-2 border-[#00E5FF]" />
          <div className="absolute bottom-2 left-2 w-4 h-4 border-b-2 border-l-2 border-[#00E5FF]" />
          <div className="absolute bottom-2 right-2 w-4 h-4 border-b-2 border-r-2 border-[#00E5FF]" />

          {/* Upload Icon & Centered Label */}
          <div className="p-5 rounded-full bg-[#00E5FF]/10 border border-[#00E5FF]/60 group-hover:scale-110 transition-transform duration-300 shadow-[0_0_20px_rgba(0,229,255,0.4)] mb-4">
            <Upload className="w-10 h-10 text-[#00E5FF]" />
          </div>

          <h2 className="font-orbitron text-2xl sm:text-4xl font-extrabold text-slate-100 tracking-wider text-center group-hover:text-[#00E5FF] transition-colors">
            UPLOAD AN IMAGE
          </h2>
          <p className="font-mono text-xs text-[#00E5FF]/90 tracking-widest mt-2 uppercase">
            Drag & Drop Up to 5 Local Files or Click to Select
          </p>
        </label>
      </div>

      {/* Uploaded Images Detection Results List (Glass Black 20% Transparency Cards) */}
      {items.length > 0 && (
        <div className="relative z-10 max-w-6xl mx-auto w-full space-y-4 pt-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {items.map((item) => (
              <GlassCard key={item.id} className="p-3 relative group bg-black/20 backdrop-blur-xl border border-[#00E5FF]/60 shadow-[0_0_20px_rgba(0,229,255,0.3)]">
                <button
                  onClick={() => removeItem(item.id)}
                  className="absolute top-2 right-2 z-30 p-1 rounded-full bg-black/80 text-slate-400 hover:text-red-400 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>

                <div className="relative aspect-video rounded overflow-hidden bg-black/50 border border-slate-800 mb-3">
                  <img src={item.url} alt={item.name} className="w-full h-full object-cover" />
                  
                  {/* Laser Scanning Beam Line */}
                  {item.isScanning && (
                    <motion.div
                      initial={{ top: '0%' }}
                      animate={{ top: ['0%', '100%', '0%'] }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                      className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#00E5FF] to-transparent shadow-[0_0_15px_#00E5FF] z-20"
                    />
                  )}
                  {item.isScanning && (
                    <div className="absolute inset-0 bg-black/70 backdrop-blur-[1px] flex items-center justify-center z-10">
                      <Scan className="w-6 h-6 text-[#00E5FF] animate-spin" />
                    </div>
                  )}
                </div>

                <div className="space-y-1">
                  <div className="font-orbitron text-xs font-bold text-slate-100 truncate">
                    {item.name}
                  </div>
                  <div className="flex items-center justify-between font-mono text-[11px] pt-1">
                    <span className={item.isAi ? 'text-[#00E5FF]' : 'text-emerald-400'}>
                      {item.isAi ? 'AI GENERATED' : 'REAL IMAGE'}
                    </span>
                    <span className="font-bold text-slate-200">
                      {item.isScanning ? '---' : `${item.isAi ? item.aiProb : item.realProb}%`}
                    </span>
                  </div>
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-1">
                    <div
                      className={`h-full transition-all duration-700 ${item.isAi ? 'bg-[#00E5FF] shadow-[0_0_10px_#00E5FF]' : 'bg-emerald-400'}`}
                      style={{ width: item.isScanning ? '0%' : `${item.isAi ? item.aiProb : item.realProb}%` }}
                    />
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      )}

      <div className="relative z-10 text-center font-mono text-[10px] text-slate-600 uppercase tracking-widest pt-6" />
    </div>
  );
};
