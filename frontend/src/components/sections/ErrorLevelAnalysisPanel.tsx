import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers,
  Image as ImageIcon,
  Target,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Info,
  Activity,
  Zap,
  ZoomIn,
  X,
  Maximize2,
  Clock,
  Sliders,
  Sparkles,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { CyberBadge } from '@/components/ui/CyberBadge';

export interface ElaObservationItem {
  title: string;
  description: string;
  severity: string;
  confidence: number;
  observation_type?: string;
}

export interface ElaMetricsData {
  average_error?: number;
  maximum_error?: number;
  minimum_error?: number;
  standard_deviation?: number;
  high_error_pixel_count?: number;
  percentage_high_error_pixels?: number;
  mean_brightness?: number;
  dynamic_range?: number;
}

export interface ElaImageData {
  base64?: string | null;
  format?: string;
  width?: number;
  height?: number;
}

export interface SuspiciousRegionItem {
  bounding_box?: {
    x?: number;
    y?: number;
    width?: number;
    height?: number;
  };
  coordinates?: number[];
  area?: number;
  intensity?: number;
}

export interface ElaPayload {
  jpeg_quality?: number;
  metrics?: ElaMetricsData;
  observations?: ElaObservationItem[];
  ela_image?: ElaImageData | null;
  suspicious_regions?: SuspiciousRegionItem[];
  ela_score?: number;
  confidence_score?: number;
}

export interface ElaModuleResultData {
  module: string;
  status: string;
  score: number;
  confidence: number;
  execution_time_ms: number;
  message: string;
  error_details?: string | null;
  data?: ElaPayload | null;
}

interface ErrorLevelAnalysisPanelProps {
  moduleResult: ElaModuleResultData;
  originalImageUrl?: string;
}

export const ErrorLevelAnalysisPanel: React.FC<ErrorLevelAnalysisPanelProps> = ({
  moduleResult,
  originalImageUrl,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [isZoomOpen, setIsZoomOpen] = useState<boolean>(false);
  const [zoomScale, setZoomScale] = useState<number>(1);

  const payload = useMemo(() => moduleResult.data || {}, [moduleResult.data]);
  const metrics = useMemo(() => payload.metrics || {}, [payload.metrics]);
  const observations = useMemo(() => payload.observations || [], [payload.observations]);
  const suspiciousRegions = useMemo(() => payload.suspicious_regions || [], [payload.suspicious_regions]);
  const elaImage = payload.ela_image;

  const elaScore = useMemo(() => payload.ela_score ?? (1 - (moduleResult.score || 0)), [payload.ela_score, moduleResult.score]);
  const confidenceScore = useMemo(() => payload.confidence_score ?? moduleResult.confidence ?? 0, [payload.confidence_score, moduleResult.confidence]);
  const jpegQuality = payload.jpeg_quality ?? 90;

  // Severity color mapping
  const getSeverityBadgeVariant = useCallback((severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'high':
        return 'red';
      case 'medium':
        return 'amber';
      case 'low':
      default:
        return 'cyan';
    }
  }, []);

  // Simplified Observation Wording Mapper
  const simplifyObservation = useCallback((obs: ElaObservationItem) => {
    const titleLower = obs.title.toLowerCase();
    const descLower = obs.description.toLowerCase();

    if (titleLower.includes('localized') || descLower.includes('localized')) {
      return {
        title: 'Localized Compression Differences',
        description: 'Some small parts of the image have different JPEG compression compared to nearby areas. This sometimes happens after editing or when an image is saved multiple times.',
      };
    }
    if (titleLower.includes('uniform') || descLower.includes('uniform compression')) {
      return {
        title: 'Uniform Compression Detected',
        description: 'The JPEG compression is consistent and even across the entire image. This is common when an image is saved once by a camera or digital software.',
      };
    }
    if (titleLower.includes('heavy') || descLower.includes('heavy jpeg')) {
      return {
        title: 'Heavy JPEG Compression',
        description: 'Noticeable compression artifacts appear across large parts of the image. This typically occurs when an image has been saved repeatedly or heavily compressed.',
      };
    }
    if (titleLower.includes('multiple') || descLower.includes('multiple compression')) {
      return {
        title: 'Multiple Compression Signatures',
        description: 'Different parts of the image show distinct compression characteristics. This pattern often appears when elements from different images are combined or saved at different quality levels.',
      };
    }
    if (titleLower.includes('edited') || titleLower.includes('suspected region') || descLower.includes('edited region')) {
      return {
        title: 'Suspected Region Variance',
        description: 'A specific area shows compression levels that differ noticeably from the rest of the image. This region may have been modified, added, or separately re-saved.',
      };
    }
    if (titleLower.includes('screenshot') || descLower.includes('screenshot')) {
      return {
        title: 'Screenshot Pattern Detected',
        description: 'The image shows a very uniform, low-error compression pattern typical of screenshots captured directly from a digital display screen.',
      };
    }
    if (titleLower.includes('synthetic') || descLower.includes('synthetic generation')) {
      return {
        title: 'Unusual Compression Uniformity',
        description: 'The compression pattern is unusually smooth and uniform. Some AI image generators produce this characteristic when rendering synthetic output, though it can also occur in uncompressed digital files.',
      };
    }
    if (titleLower.includes('camera') || descLower.includes('camera compression')) {
      return {
        title: 'Consistent Camera Compression',
        description: 'Compression characteristics are uniform across the entire image, matching what is typically seen in an original camera photograph.',
      };
    }

    return {
      title: obs.title,
      description: obs.description,
    };
  }, []);

  // ELA Verdict Determination (Enterprise Summary)
  const elaVerdict = useMemo(() => {
    if (elaScore >= 0.75) {
      return {
        label: 'Consistent Compression',
        variant: 'emerald' as const,
        description: 'JPEG compression patterns are uniform across the image. This typically indicates single-pass saving, but does not rule out all forms of synthetic generation or editing.',
      };
    } else if (elaScore >= 0.4) {
      return {
        label: 'Anomalous Compression',
        variant: 'amber' as const,
        description: 'We found areas in the image where JPEG compression differs from the surrounding regions. This can happen after image editing, multiple saves, or other image processing. This alone does not prove manipulation.',
      };
    } else {
      return {
        label: 'Compression Inconsistencies',
        variant: 'red' as const,
        description: 'We found areas in the image where JPEG compression differs from the surrounding regions. This can happen after image editing, multiple saves, or other image processing. This alone does not prove manipulation.',
      };
    }
  }, [elaScore]);

  const verdict = elaVerdict;

  // Format metric helper
  const formatMetric = (value?: number, decimals: number = 2): string => {
    if (value === undefined || value === null) return 'N/A';
    return value.toFixed(decimals);
  };

  return (
    <GlassCard className="w-full bg-black/30 backdrop-blur-xl border border-[#FF006E]/40 shadow-[0_0_30px_rgba(255,0,110,0.25)] relative overflow-hidden transition-all duration-300">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-[#FF006E]/10 border border-[#FF006E]/50 text-[#FF006E] shadow-[0_0_15px_rgba(255,0,110,0.4)]">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-orbitron text-lg font-bold text-slate-100 tracking-wide">
                ERROR LEVEL ANALYSIS
              </h3>
              <CyberBadge label="Completed" variant="emerald" pulse={false} />
              <CyberBadge label={verdict.label} variant={verdict.variant} pulse={true} />
            </div>
            <p className="font-mono text-xs text-slate-400 mt-0.5 flex items-center gap-2">
              <span>Forensic ELA Engine</span>
              <span>•</span>
              <span>JPEG Quality: {jpegQuality}%</span>
              <span>•</span>
              <span className="flex items-center gap-1 text-pink-300 font-bold">
                <Clock className="w-3 h-3 text-[#FF006E]" /> {moduleResult.execution_time_ms}ms
              </span>
            </p>
          </div>
        </div>

        {/* Expand / Collapse Button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-black/40 border border-[#FF006E]/40 text-xs font-mono text-[#FF006E] hover:border-[#FF006E] hover:bg-[#FF006E]/10 transition-all cursor-pointer self-start sm:self-auto"
        >
          {isExpanded ? (
            <>
              [ COLLAPSE ] <ChevronUp className="w-4 h-4" />
            </>
          ) : (
            <>
              [ EXPAND DETAILS ] <ChevronDown className="w-4 h-4" />
            </>
          )}
        </button>
      </div>

      {/* Forensic Scope & Limitations Section */}
      <div className="mt-4 p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/40 text-amber-200 flex items-start gap-2.5 text-xs font-mono leading-relaxed">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-white uppercase font-bold">Important:</strong> Error Level Analysis only examines JPEG compression patterns. AI-generated images, screenshots, edited photos, and repeatedly saved images can sometimes produce similar ELA results. Always interpret ELA together with Metadata Analysis and other forensic modules.
        </div>
      </div>

      {/* ELA Overall Summary Banner */}
      <div className="mt-3 p-3.5 rounded-lg bg-[#FF006E]/10 border border-[#FF006E]/40 text-pink-200 text-xs font-mono flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-start gap-2.5">
          <Zap className="w-4 h-4 text-[#FF006E] shrink-0 mt-0.5" />
          <div>
            <strong className="text-white uppercase font-bold block mb-0.5">Overall ELA Summary:</strong>
            <p className="leading-relaxed text-slate-200">{verdict.description}</p>
          </div>
        </div>
        <div className="text-[11px] text-slate-400 font-mono self-end sm:self-auto">
          JPEG Resaved Quality: <span className="text-[#FF006E] font-bold">{jpegQuality}%</span>
        </div>
      </div>

      {/* Score Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {/* ELA Score */}
        <div className="p-4 rounded-lg bg-black/40 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between font-mono text-xs mb-1.5">
              <span className="text-slate-300 font-bold uppercase">ELA Score: {(elaScore * 100).toFixed(1)}%</span>
              <span className="font-bold text-[#FF006E] text-sm">{(elaScore * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden mb-2">
              <div
                className={`h-full transition-all duration-700 ${
                  elaScore >= 0.75 ? 'bg-emerald-400' : elaScore >= 0.4 ? 'bg-amber-400' : 'bg-[#FF006E]'
                }`}
                style={{ width: `${(elaScore * 100).toFixed(1)}%` }}
              />
            </div>
            <p className="font-mono text-xs text-slate-300 leading-relaxed">
              Higher scores indicate more consistent JPEG compression across the image, while lower scores suggest greater compression differences that may deserve closer inspection.
            </p>
          </div>
          <p className="font-mono text-[10px] text-slate-500 mt-2 border-t border-slate-900 pt-1.5">
            Note: ELA score measures compression uniformity across the image.
          </p>
        </div>

        {/* Confidence Score */}
        <div className="p-4 rounded-lg bg-black/40 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between font-mono text-xs mb-1.5">
              <span className="text-slate-300 font-bold uppercase">Analysis Confidence</span>
              <span className="font-bold text-emerald-400 text-sm">{(confidenceScore * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden mb-2">
              <div
                className="h-full bg-emerald-400 transition-all duration-700"
                style={{ width: `${(confidenceScore * 100).toFixed(1)}%` }}
              />
            </div>
            <p className="font-mono text-xs text-slate-300 leading-relaxed">
              This confidence measures how reliable the ELA analysis is—not whether the image is real or fake.
            </p>
          </div>
          <p className="font-mono text-[10px] text-slate-500 mt-2 border-t border-slate-900 pt-1.5">
            Evaluated based on image dimensions, pixel variance, and compression signal clarity.
          </p>
        </div>
      </div>

      {/* Expanded Detailed Inspection Panels */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="space-y-6 pt-6 mt-6 border-t border-slate-800"
          >
            {/* Section 1: ELA Image Visualization — Side-by-Side Comparison */}
            <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#FF006E] uppercase">
                  <ImageIcon className="w-4 h-4 text-[#FF006E]" /> Side-by-Side Image vs ELA Heatmap
                </div>
                {elaImage?.base64 && (
                  <button
                    onClick={() => { setZoomScale(1); setIsZoomOpen(true); }}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#FF006E]/10 border border-[#FF006E]/40 text-[11px] font-mono text-[#FF006E] hover:bg-[#FF006E]/20 transition-all cursor-pointer"
                  >
                    <ZoomIn className="w-3.5 h-3.5" /> [ ZOOM & INSPECT ]
                  </button>
                )}
              </div>

              {/* Side by Side Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Original Image */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
                    <span>ORIGINAL IMAGE</span>
                    <span>Reference</span>
                  </div>
                  <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center min-h-[220px]">
                    {originalImageUrl ? (
                      <img
                        src={originalImageUrl}
                        alt="Original Upload"
                        className="w-full h-auto max-h-[340px] object-contain"
                      />
                    ) : (
                      <p className="font-mono text-xs text-slate-600">Original Image</p>
                    )}
                  </div>
                </div>

                {/* Generated ELA Image */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-mono text-pink-300 px-1 font-bold">
                    <span>GENERATED ELA HEATMAP</span>
                    <span>Q={jpegQuality}%</span>
                  </div>
                  <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center min-h-[220px]">
                    {elaImage?.base64 ? (
                      <>
                        <img
                          src={`data:image/${elaImage.format || 'png'};base64,${elaImage.base64}`}
                          alt="ELA Analysis Heatmap"
                          className="w-full h-auto max-h-[340px] object-contain cursor-pointer hover:scale-[1.02] transition-transform"
                          onClick={() => { setZoomScale(1); setIsZoomOpen(true); }}
                        />
                        <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/70 text-[10px] font-mono text-slate-300 border border-slate-800">
                          {elaImage.width}×{elaImage.height}px
                        </div>
                      </>
                    ) : (
                      <p className="font-mono text-xs text-slate-500">No ELA heatmap generated.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Section 2: ELA Compression Metrics Grid */}
            <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#FF006E] uppercase border-b border-slate-800 pb-2">
                <Sliders className="w-4 h-4 text-[#FF006E]" /> Compression Error Metrics
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* Average Error */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">Average Error</span>
                  <span className="font-bold text-slate-100 font-mono text-base block">{formatMetric(metrics.average_error)}</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    The average compression difference across the image. Lower values usually indicate more uniform compression.
                  </p>
                </div>

                {/* Maximum Error */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">Maximum Error</span>
                  <span className="font-bold text-slate-100 font-mono text-base block">{formatMetric(metrics.maximum_error)}</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    The highest compression error found in any single pixel or region.
                  </p>
                </div>

                {/* Minimum Error */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">Minimum Error</span>
                  <span className="font-bold text-slate-100 font-mono text-base block">{formatMetric(metrics.minimum_error)}</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    The lowest compression error detected across the image pixels.
                  </p>
                </div>

                {/* Standard Deviation */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">Standard Deviation</span>
                  <span className="font-bold text-slate-100 font-mono text-base block">{formatMetric(metrics.standard_deviation)}</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    Measures how widely compression errors vary across the image. Lower values mean more consistent compression.
                  </p>
                </div>

                {/* % High Error Pixels */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">% High Error Pixels</span>
                  <span className="font-bold text-[#FF006E] font-mono text-base block">{formatMetric(metrics.percentage_high_error_pixels)}%</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    The percentage of pixels showing error levels significantly higher than average.
                  </p>
                </div>

                {/* High Error Pixel Count */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">High Error Pixels</span>
                  <span className="font-bold text-slate-100 font-mono text-base block">{metrics.high_error_pixel_count?.toLocaleString() || '0'}</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    The total count of pixels showing error levels significantly higher than average.
                  </p>
                </div>

                {/* Mean Brightness */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">Mean Brightness</span>
                  <span className="font-bold text-slate-100 font-mono text-base block">{formatMetric(metrics.mean_brightness)}</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    The average brightness level of the ELA difference map.
                  </p>
                </div>

                {/* Dynamic Range */}
                <div className="p-3 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                  <span className="text-slate-400 block font-mono text-xs font-bold uppercase">Dynamic Range</span>
                  <span className="font-bold text-slate-100 font-mono text-base block">{formatMetric(metrics.dynamic_range)}</span>
                  <p className="text-[11px] font-mono text-slate-400 leading-snug">
                    The difference between the maximum and minimum error values across the heatmap.
                  </p>
                </div>
              </div>
            </div>

            {/* Section 3: Suspicious Regions */}
            <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#FF006E] uppercase border-b border-slate-800 pb-2">
                <Target className="w-4 h-4 text-[#FF006E]" /> Suspicious Regions ({suspiciousRegions.length})
              </div>

              {suspiciousRegions.length > 0 ? (
                <div className="space-y-3">
                  <div className="p-3 rounded bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs font-mono leading-relaxed">
                    We found {suspiciousRegions.length} small region{suspiciousRegions.length > 1 ? 's' : ''} with compression patterns that differ from the surrounding image. These areas may have been affected by editing or additional image processing, but they are not conclusive proof of manipulation.
                  </div>
                  <div className="space-y-2">
                    {suspiciousRegions.map((region, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded bg-slate-950/60 border border-slate-800 flex items-center justify-between gap-3 text-xs font-mono flex-wrap"
                      >
                        <div className="space-y-1 w-full">
                          <div className="flex items-center gap-2 font-bold text-slate-100">
                            <span>Region #{idx + 1}</span>
                            <CyberBadge
                              label={region.intensity ? `Intensity: ${region.intensity.toFixed(2)}` : 'High Variance'}
                              variant="red"
                              pulse={false}
                            />
                          </div>
                          <div className="text-slate-400 text-[11px]">
                            Bounding Box: x={region.bounding_box?.x ?? region.coordinates?.[0] ?? 0}, y={region.bounding_box?.y ?? region.coordinates?.[1] ?? 0},{' '}
                            w={region.bounding_box?.width ?? ((region.coordinates?.[2] ?? 0) - (region.coordinates?.[0] ?? 0))}, h={region.bounding_box?.height ?? ((region.coordinates?.[3] ?? 0) - (region.coordinates?.[1] ?? 0))}
                            {region.area ? ` • Area: ${region.area.toFixed(0)} pixels` : ''}
                          </div>
                          <p className="text-slate-300 text-[11px] pt-1">
                            This localized area shows compression levels that differ from surrounding regions, which can occur after editing, compositing, or repeated saving.
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 font-mono text-xs text-emerald-400 pt-1 p-2 rounded bg-emerald-500/10 border border-emerald-500/20">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>No suspicious regions found. The JPEG compression patterns appear consistent across the entire image.</span>
                </div>
              )}
            </div>

            {/* Section 4: Forensic Observations */}
            <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#FF006E] uppercase border-b border-slate-800 pb-2">
                <Activity className="w-4 h-4 text-[#FF006E]" /> ELA Forensic Observations ({observations.length})
              </div>

              {observations.length > 0 ? (
                <div className="space-y-2">
                  {observations.map((obs, idx) => {
                    const simplified = simplifyObservation(obs);
                    return (
                      <div
                        key={idx}
                        className="p-3 rounded bg-slate-950/60 border border-slate-800 flex items-start justify-between gap-3 text-xs font-mono"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 font-bold text-slate-100 flex-wrap">
                            <span>{simplified.title}</span>
                            <CyberBadge
                              label={obs.severity}
                              variant={getSeverityBadgeVariant(obs.severity)}
                              pulse={false}
                            />
                          </div>
                          <p className="text-slate-300 leading-relaxed">{simplified.description}</p>
                        </div>
                        <div className="text-right text-[11px] text-slate-500 shrink-0 font-bold">
                          Conf: {(obs.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="font-mono text-xs text-slate-500 p-2">No forensic observations recorded for this image.</p>
              )}
            </div>

            {/* Section 5: Engine Execution & Diagnostic Details */}
            <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#FF006E] uppercase border-b border-slate-800 pb-2">
                <Sparkles className="w-4 h-4 text-[#FF006E]" /> Module Execution Diagnostic
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
                <div className="p-2.5 rounded bg-slate-950/40 border border-slate-800">
                  <span className="text-slate-500 block text-[10px]">JPEG QUALITY</span>
                  <span className="text-slate-200 font-bold">{jpegQuality}%</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950/40 border border-slate-800">
                  <span className="text-slate-500 block text-[10px]">ELA SCORE</span>
                  <span className="text-[#FF006E] font-bold">{(elaScore * 100).toFixed(1)}%</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950/40 border border-slate-800">
                  <span className="text-slate-500 block text-[10px]">EXECUTION TIME</span>
                  <span className="text-slate-200 font-bold">{moduleResult.execution_time_ms} ms</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950/40 border border-slate-800">
                  <span className="text-slate-500 block text-[10px]">MODULE STATUS</span>
                  <span className={`font-bold ${moduleResult.status === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
                    {moduleResult.status.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Side-by-Side Zoom Modal */}
      <AnimatePresence>
        {isZoomOpen && elaImage?.base64 && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative max-w-6xl w-full bg-[#030712] border border-[#FF006E]/60 rounded-xl p-6 shadow-[0_0_50px_rgba(255,0,110,0.4)] overflow-hidden space-y-4 max-h-[90vh] flex flex-col"
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3 font-orbitron font-bold text-slate-100 text-lg">
                  <Maximize2 className="w-5 h-5 text-[#FF006E]" /> Side-by-Side ELA High-Res Inspection
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 bg-black/60 px-3 py-1 rounded border border-slate-800 text-xs font-mono text-slate-300">
                    <span>Zoom:</span>
                    <button
                      onClick={() => setZoomScale((s) => Math.max(0.8, s - 0.2))}
                      className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-white font-bold"
                    >
                      -
                    </button>
                    <span>{(zoomScale * 100).toFixed(0)}%</span>
                    <button
                      onClick={() => setZoomScale((s) => Math.min(2.5, s + 0.2))}
                      className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-white font-bold"
                    >
                      +
                    </button>
                    <button
                      onClick={() => setZoomScale(1)}
                      className="text-[10px] text-pink-400 underline ml-1"
                    >
                      Reset
                    </button>
                  </div>

                  <button
                    onClick={() => setIsZoomOpen(false)}
                    className="p-1.5 rounded-full bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-[#FF006E] transition-all"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Side-by-Side Zoom Canvas */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-auto p-2">
                {/* Original Image */}
                <div className="space-y-2">
                  <span className="font-mono text-xs font-bold text-slate-400 block">ORIGINAL REFERENCE</span>
                  <div className="overflow-auto max-h-[60vh] border border-slate-800 rounded bg-slate-950 flex items-center justify-center p-2">
                    {originalImageUrl && (
                      <img
                        src={originalImageUrl}
                        alt="Original"
                        style={{ transform: `scale(${zoomScale})`, transformOrigin: 'top left' }}
                        className="transition-transform duration-200 max-w-full h-auto"
                      />
                    )}
                  </div>
                </div>

                {/* ELA Heatmap */}
                <div className="space-y-2">
                  <span className="font-mono text-xs font-bold text-[#FF006E] block">ELA FORENSIC HEATMAP</span>
                  <div className="overflow-auto max-h-[60vh] border border-slate-800 rounded bg-slate-950 flex items-center justify-center p-2">
                    <img
                      src={`data:image/${elaImage.format || 'png'};base64,${elaImage.base64}`}
                      alt="ELA Zoom"
                      style={{ transform: `scale(${zoomScale})`, transformOrigin: 'top left' }}
                      className="transition-transform duration-200 max-w-full h-auto"
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
};
