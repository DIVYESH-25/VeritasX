import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Scan, ArrowLeft, AlertTriangle, CheckCircle, Sparkles, X, ShieldCheck } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useCursorState } from '@/hooks/useCursorState';
import { MetadataAnalysisPanel, ModuleResultData } from '@/components/sections/MetadataAnalysisPanel';

export interface UploadedMediaItem {
  id: string;
  name: string;
  url: string;
  file: File;
  isScanning: boolean;
  error?: string | null;
  orchestratorData?: {
    request_id: string;
    total_execution_time_ms: number;
    status: string;
    aggregated_result: any;
    metadataResult?: ModuleResultData;
  } | null;
}

interface BatchDetectionWorkspaceProps {
  onBackToHero: () => void;
}

export const BatchDetectionWorkspace: React.FC<BatchDetectionWorkspaceProps> = ({ onBackToHero }) => {
  const { setCursor, resetCursor } = useCursorState();
  const [items, setItems] = useState<UploadedMediaItem[]>([]);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  // Analyze single file via Backend API
  const analyzeFileOnBackend = async (itemId: string, file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      // Try proxy route first, fallback to direct backend URL if proxy fails or returns 5xx error
      let response: Response;
      try {
        response = await fetch('/api/v1/analyze', {
          method: 'POST',
          body: formData,
        });
        if (!response.ok && response.status >= 500) {
          try {
            const directResp = await fetch('http://localhost:8000/api/v1/analyze', {
              method: 'POST',
              body: formData,
            });
            if (directResp.ok) {
              response = directResp;
            }
          } catch {
            // direct fetch also failed, keep original response
          }
        }
      } catch {
        response = await fetch('http://localhost:8000/api/v1/analyze', {
          method: 'POST',
          body: formData,
        });
      }

      if (!response.ok) {
        let msg = `Server error (${response.status})`;
        try {
          const rawText = await response.text();
          try {
            const errJson = JSON.parse(rawText);
            if (errJson && errJson.detail) {
              msg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
            } else if (rawText) {
              msg += `: ${rawText}`;
            }
          } catch {
            if (rawText) msg += `: ${rawText}`;
          }
        } catch {
          // If reading response body fails
        }
        throw new Error(msg);
      }

      const responseJson = await response.json();
      const metadataModule = (responseJson.modules || []).find(
        (m: any) => m.module === 'Metadata Analysis'
      );

      setItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? {
                ...it,
                isScanning: false,
                orchestratorData: {
                  request_id: responseJson.request_id,
                  total_execution_time_ms: responseJson.total_execution_time_ms,
                  status: responseJson.status,
                  aggregated_result: responseJson.aggregated_result,
                  metadataResult: metadataModule,
                },
              }
            : it
        )
      );
    } catch (err: any) {
      console.error('API Error during image analysis:', err);
      setItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? {
                ...it,
                isScanning: false,
                error: err.message || 'Failed to connect to backend server',
              }
            : it
        )
      );
    }
  };

  // Process uploaded files (Max 4 limit)
  const processFiles = (fileList: FileList | File[]) => {
    const files = Array.from(fileList).slice(0, 4);
    if (!files.length) return;

    const newItems: UploadedMediaItem[] = files.map((file, i) => {
      const itemId = `uploaded-${Date.now()}-${i}`;
      return {
        id: itemId,
        name: file.name,
        url: URL.createObjectURL(file),
        file,
        isScanning: true,
        error: null,
        orchestratorData: null,
      };
    });

    setItems((prev) => [...prev, ...newItems]);

    // Dispatch backend API request for each file
    newItems.forEach((item) => {
      analyzeFileOnBackend(item.id, item.file);
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

      {/* Center: UPLOAD AN IMAGE Drag & Drop Zone */}
      <div className="relative z-10 max-w-4xl mx-auto w-full my-6 py-4">
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
          className={`flex flex-col items-center justify-center p-10 sm:p-12 rounded-xl border-2 border-dashed backdrop-blur-xl transition-all duration-300 cursor-none relative overflow-hidden group ${
            isDragOver
              ? 'bg-black/40 border-[#00E5FF] shadow-[0_0_50px_rgba(0,229,255,0.6)] scale-105'
              : 'bg-black/20 border-[#00E5FF]/60 hover:border-[#00E5FF] hover:bg-black/30 shadow-[0_0_30px_rgba(0,229,255,0.3)] hover:shadow-[0_0_50px_rgba(0,229,255,0.7)]'
          }`}
        >
          <div className="p-4 rounded-full bg-[#00E5FF]/10 border border-[#00E5FF]/60 group-hover:scale-110 transition-transform duration-300 shadow-[0_0_20px_rgba(0,229,255,0.4)] mb-3">
            <Upload className="w-8 h-8 text-[#00E5FF]" />
          </div>

          <h2 className="font-orbitron text-xl sm:text-3xl font-extrabold text-slate-100 tracking-wider text-center group-hover:text-[#00E5FF] transition-colors">
            UPLOAD AN IMAGE
          </h2>
          <p className="font-mono text-xs text-[#00E5FF]/90 tracking-widest mt-2 uppercase">
            Drag & Drop Up to 4 Local Files or Click to Select (JPEG, PNG, WEBP)
          </p>
        </label>
      </div>

      {/* Uploaded Images Forensic Metadata Analysis Results List */}
      {items.length > 0 && (
        <div className="relative z-10 max-w-6xl mx-auto w-full space-y-6 pt-2">
          {items.map((item) => (
            <div key={item.id} className="relative space-y-3">
              {/* Image Preview & Status Row */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-lg bg-black/40 border border-[#00E5FF]/40 backdrop-blur-xl gap-4">
                <div className="flex items-center gap-4">
                  <div className="relative w-20 h-14 rounded overflow-hidden bg-black/60 border border-slate-800 shrink-0">
                    <img src={item.url} alt={item.name} className="w-full h-full object-cover" />
                    {item.isScanning && (
                      <div className="absolute inset-0 bg-black/70 backdrop-blur-[1px] flex items-center justify-center">
                        <Scan className="w-5 h-5 text-[#00E5FF] animate-spin" />
                      </div>
                    )}
                  </div>
                  <div>
                    <h4 className="font-orbitron text-sm font-bold text-slate-100 truncate max-w-xs sm:max-w-md">
                      {item.name}
                    </h4>
                    <p className="font-mono text-xs text-slate-400 mt-0.5">
                      {item.file.type || 'image/jpeg'} • {(item.file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {item.isScanning && (
                    <span className="font-mono text-xs text-[#00E5FF] flex items-center gap-2 animate-pulse">
                      <Scan className="w-4 h-4 animate-spin" /> ANALYZING METADATA...
                    </span>
                  )}

                  {item.error && (
                    <span className="font-mono text-xs text-red-400 flex items-center gap-1.5 bg-red-500/10 px-2.5 py-1 rounded border border-red-500/30">
                      <AlertTriangle className="w-4 h-4" /> {item.error}
                    </span>
                  )}

                  <button
                    onClick={() => removeItem(item.id)}
                    className="p-1.5 rounded-full bg-black/60 text-slate-400 hover:text-red-400 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Render Metadata Analysis Panel when complete */}
              {item.orchestratorData?.metadataResult && (
                <MetadataAnalysisPanel moduleResult={item.orchestratorData.metadataResult} />
              )}
            </div>
          ))}
        </div>
      )}

      <div className="relative z-10 text-center font-mono text-[10px] text-slate-600 uppercase tracking-widest pt-6" />
    </div>
  );
};
