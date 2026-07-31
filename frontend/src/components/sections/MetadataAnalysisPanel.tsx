import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Image as ImageIcon,
  Camera,
  Cpu,
  MapPin,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Info,
  Copy,
  Check,
  Sparkles,
  Search,
  Activity,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { CyberBadge } from '@/components/ui/CyberBadge';

export interface ValidationIssueItem {
  type: string;
  severity: string;
  description: string;
  field?: string;
}

export interface ObservationItem {
  title: string;
  description: string;
  severity: string;
  confidence: number;
  observation_type?: string;
}

export interface MetadataPayload {
  file?: {
    filename?: string;
    extension?: string;
    mime_type?: string;
    file_size?: number;
    sha256?: string;
    md5?: string;
  };
  image?: {
    width?: number;
    height?: number;
    aspect_ratio?: number;
    color_mode?: string;
    color_profile?: string;
    bit_depth?: number;
    compression_type?: string;
    dpi?: [number, number] | null;
    format?: string;
  };
  exif?: {
    camera_make?: string | null;
    camera_model?: string | null;
    lens?: string | null;
    lens_make?: string | null;
    software?: string | null;
    artist?: string | null;
    copyright?: string | null;
    datetime_original?: string | null;
    datetime_digitized?: string | null;
    datetime_modified?: string | null;
    exposure_time?: string | null;
    aperture?: string | null;
    iso?: number | null;
    flash?: string | null;
    focal_length?: string | null;
    white_balance?: string | null;
    gps?: {
      latitude?: number | null;
      longitude?: number | null;
      altitude?: number | null;
      timestamp?: string | null;
    } | null;
    has_exif?: boolean;
    exif_field_count?: number;
  };
  validation?: {
    total_issues?: number;
    issues_by_severity?: Record<string, number>;
    issues?: ValidationIssueItem[];
  };
  observations?: ObservationItem[];
  metadata_score?: number;
  confidence_score?: number;
}

export interface ModuleResultData {
  module: string;
  status: string;
  score: number;
  confidence: number;
  execution_time_ms: number;
  message: string;
  error_details?: string | null;
  data?: MetadataPayload | null;
}

interface MetadataAnalysisPanelProps {
  moduleResult: ModuleResultData;
}

export const MetadataAnalysisPanel: React.FC<MetadataAnalysisPanelProps> = ({ moduleResult }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const payload = useMemo(() => moduleResult.data || {}, [moduleResult.data]);
  const file = useMemo(() => payload.file || {}, [payload.file]);
  const image = useMemo(() => payload.image || {}, [payload.image]);
  const exif = useMemo(() => payload.exif || {}, [payload.exif]);
  const validation = useMemo(() => payload.validation || {}, [payload.validation]);
  const observations = useMemo(() => payload.observations || [], [payload.observations]);

  const metadataScore = useMemo(() => payload.metadata_score ?? (1 - (moduleResult.score || 0)), [payload.metadata_score, moduleResult.score]);
  const confidenceScore = useMemo(() => payload.confidence_score ?? moduleResult.confidence ?? 0, [payload.confidence_score, moduleResult.confidence]);

  // Format file size
  const formatFileSize = useCallback((bytes?: number): string => {
    if (!bytes) return 'Not Available';
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} Bytes`;
  }, []);

  // Copy to clipboard helper
  const handleCopy = useCallback((text: string, fieldName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  }, []);

  // Metadata Verdict Determination (Metadata-specific)
  const getMetadataVerdict = () => {
    const aiObs = observations.find(
      (o) =>
        o.observation_type === 'saved_stable_diffusion' ||
        o.observation_type === 'saved_midjourney'
    );
    if (aiObs) {
      return {
        label: 'AI Generator Signature Detected',
        variant: 'red' as const,
        description: 'EXIF software headers match known AI generator signatures.',
      };
    }

    if (metadataScore >= 0.75) {
      return {
        label: 'Organic Camera Metadata',
        variant: 'emerald' as const,
        description: 'Rich EXIF tags consistent with authentic hardware capture.',
      };
    } else if (metadataScore >= 0.4) {
      return {
        label: 'Modified / Processed Metadata',
        variant: 'amber' as const,
        description: 'Metadata shows signs of software editing or re-saving.',
      };
    } else {
      return {
        label: 'Metadata Stripped / Suspicious',
        variant: 'purple' as const,
        description: 'EXIF metadata is absent or heavily stripped.',
      };
    }
  };

  const verdict = getMetadataVerdict();

  // Nuanced Metadata Assessment Statement
  const getAssessmentStatement = () => {
    const hasAiSig = observations.some(
      (o) =>
        o.observation_type === 'saved_stable_diffusion' ||
        o.observation_type === 'saved_midjourney'
    );
    const isEdited = observations.some(
      (o) =>
        o.observation_type === 'edited_photoshop' ||
        o.observation_type === 'exported_gimp' ||
        o.observation_type === 'exported_canva'
    );

    if (hasAiSig) {
      return 'Metadata Assessment: Software headers contain explicit AI generator signatures.';
    } else if (isEdited) {
      return 'Metadata Assessment: Metadata indicates the image was processed or exported using image editing software.';
    } else if (!exif.has_exif) {
      return 'Metadata Assessment: No EXIF metadata present. Metadata may have been stripped during export or upload.';
    } else {
      return 'Metadata Assessment: No metadata indicators of AI generation were found.';
    }
  };

  // Severity color mapping
  const getSeverityBadgeVariant = (severity: string) => {
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
  };

  return (
    <GlassCard className="w-full bg-black/30 backdrop-blur-xl border border-[#00E5FF]/40 shadow-[0_0_30px_rgba(0,229,255,0.25)] relative overflow-hidden transition-all duration-300">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-[#00E5FF]/10 border border-[#00E5FF]/50 text-[#00E5FF] shadow-[0_0_15px_rgba(0,229,255,0.4)]">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-orbitron text-lg font-bold text-slate-100 tracking-wide">
                METADATA ANALYSIS
              </h3>
              <CyberBadge label="Completed" variant="emerald" pulse={false} />
              <CyberBadge label={verdict.label} variant={verdict.variant} pulse={true} />
            </div>
            <p className="font-mono text-xs text-slate-400 mt-0.5">
              Forensic Metadata Engine • Execution: {moduleResult.execution_time_ms}ms
            </p>
          </div>
        </div>

        {/* Expand / Collapse Button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-black/40 border border-[#00E5FF]/40 text-xs font-mono text-[#00E5FF] hover:border-[#00E5FF] transition-all cursor-pointer self-start sm:self-auto"
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

      {/* Mandatory Disclaimer Box */}
      <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-start gap-2.5 text-xs font-mono">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">FORENSIC DISCLAIMER:</span> This verdict is based only on metadata analysis. Other forensic modules (Error Level Analysis, Frequency Analysis, Sensor Noise) have not yet been executed.
        </div>
      </div>

      {/* Nuanced Metadata Assessment Banner */}
      <div className="mt-3 p-3 rounded-lg bg-[#00E5FF]/5 border border-[#00E5FF]/30 text-cyan-200 text-xs font-mono flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-[#00E5FF] shrink-0" />
        <span>{getAssessmentStatement()}</span>
      </div>

      {/* Score Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {/* Metadata Score */}
        <div className="p-4 rounded-lg bg-black/40 border border-slate-800">
          <div className="flex items-center justify-between font-mono text-xs mb-1.5">
            <span className="text-slate-400">METADATA INTEGRITY SCORE</span>
            <span className="font-bold text-[#00E5FF]">{(metadataScore * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-700 ${
                metadataScore >= 0.7 ? 'bg-emerald-400' : metadataScore >= 0.4 ? 'bg-amber-400' : 'bg-[#00E5FF]'
              }`}
              style={{ width: `${(metadataScore * 100).toFixed(1)}%` }}
            />
          </div>
          <p className="font-mono text-[10px] text-slate-500 mt-1">
            0% = Stripped / Suspicious • 100% = Authentic Hardware Capture
          </p>
        </div>

        {/* Confidence Score */}
        <div className="p-4 rounded-lg bg-black/40 border border-slate-800">
          <div className="flex items-center justify-between font-mono text-xs mb-1.5">
            <span className="text-slate-400">ANALYSIS CONFIDENCE</span>
            <span className="font-bold text-emerald-400">{(confidenceScore * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-400 transition-all duration-700"
              style={{ width: `${(confidenceScore * 100).toFixed(1)}%` }}
            />
          </div>
          <p className="font-mono text-[10px] text-slate-500 mt-1">
            Confidence based on EXIF tag richness and signal clarity
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
            {/* Section 1: File Information & Image Information */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* File Info Card */}
              <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#00E5FF] uppercase border-b border-slate-800 pb-2">
                  <FileText className="w-4 h-4 text-[#00E5FF]" /> File Information
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block">Filename:</span>
                    <span className="text-slate-200 truncate block">{file.filename || 'uploaded_image'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Extension:</span>
                    <span className="text-slate-200 uppercase">{file.extension || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">File Size:</span>
                    <span className="text-slate-200">{formatFileSize(file.file_size)}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">MIME Type:</span>
                    <span className="text-slate-200">{file.mime_type || 'image/jpeg'}</span>
                  </div>
                </div>

                {/* Cryptographic Hashes */}
                <div className="pt-2 border-t border-slate-800/60 space-y-1.5 font-mono text-[11px]">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>SHA-256:</span>
                    <button
                      onClick={() => file.sha256 && handleCopy(file.sha256, 'sha256')}
                      className="text-xs text-[#00E5FF] hover:text-white flex items-center gap-1 cursor-pointer"
                    >
                      {copiedField === 'sha256' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                  <div className="p-1.5 rounded bg-slate-950 font-mono text-[10px] text-slate-300 break-all border border-slate-800">
                    {file.sha256 || 'N/A'}
                  </div>
                </div>
              </div>

              {/* Image Info Card */}
              <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#00E5FF] uppercase border-b border-slate-800 pb-2">
                  <ImageIcon className="w-4 h-4 text-[#00E5FF]" /> Image Specifications
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block">Dimensions:</span>
                    <span className="text-slate-200">{image.width && image.height ? `${image.width} × ${image.height} px` : 'Not Available'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">DPI:</span>
                    <span className="text-slate-200">{image.dpi ? `${image.dpi[0]} × ${image.dpi[1]}` : 'Not Available'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Color Mode:</span>
                    <span className="text-slate-200">{image.color_mode || 'RGB'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Bit Depth:</span>
                    <span className="text-slate-200">{image.bit_depth ? `${image.bit_depth}-bit` : '8-bit'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Compression:</span>
                    <span className="text-slate-200">{image.compression_type || 'Standard'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Format:</span>
                    <span className="text-slate-200 uppercase">{image.format || 'JPEG'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Section 2: Camera Information & Software Information */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Camera Info Card */}
              <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#00E5FF] uppercase">
                    <Camera className="w-4 h-4 text-[#00E5FF]" /> Camera Hardware
                  </div>
                  <CyberBadge
                    label={exif.camera_make ? 'Hardware EXIF Found' : 'Camera Info Missing'}
                    variant={exif.camera_make ? 'emerald' : 'amber'}
                    pulse={false}
                  />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block">Camera Make:</span>
                    <span className="text-slate-200 font-bold">{exif.camera_make || 'Not Available'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Camera Model:</span>
                    <span className="text-slate-200">{exif.camera_model || 'Not Available'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Lens Spec:</span>
                    <span className="text-slate-200 truncate block">{exif.lens || 'Not Available'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">ISO Rating:</span>
                    <span className="text-slate-200">{exif.iso ? `ISO ${exif.iso}` : 'Not Available'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Aperture:</span>
                    <span className="text-slate-200">{exif.aperture || 'Not Available'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Exposure Time:</span>
                    <span className="text-slate-200">{exif.exposure_time || 'Not Available'}</span>
                  </div>
                </div>
              </div>

              {/* Software Information & GPS */}
              <div className="space-y-4">
                {/* Software Card */}
                <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#00E5FF] uppercase border-b border-slate-800 pb-2">
                    <Cpu className="w-4 h-4 text-[#00E5FF]" /> Software / Processing Tags
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono pt-1">
                    <span className="text-slate-400">Software EXIF Tag:</span>
                    <span className="font-bold text-slate-100">
                      {exif.software ? exif.software : 'Unknown / None Detected'}
                    </span>
                  </div>
                </div>

                {/* GPS Card */}
                <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#00E5FF] uppercase">
                      <MapPin className="w-4 h-4 text-[#00E5FF]" /> GPS Geolocation
                    </div>
                    <CyberBadge
                      label={exif.gps?.latitude ? 'GPS Available' : 'GPS Metadata Not Found'}
                      variant={exif.gps?.latitude ? 'emerald' : 'purple'}
                      pulse={false}
                    />
                  </div>
                  {exif.gps?.latitude && exif.gps?.longitude ? (
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                      <div>
                        <span className="text-slate-500 block">Latitude:</span>
                        <span className="text-slate-200">{exif.gps.latitude.toFixed(6)}°</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Longitude:</span>
                        <span className="text-slate-200">{exif.gps.longitude.toFixed(6)}°</span>
                      </div>
                    </div>
                  ) : (
                    <p className="font-mono text-xs text-slate-500 pt-1">
                      No GPS coordinates embedded in EXIF payload.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Section 3: Metadata Observations */}
            <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#00E5FF] uppercase border-b border-slate-800 pb-2">
                <Activity className="w-4 h-4 text-[#00E5FF]" /> Forensic Observations ({observations.length})
              </div>

              {observations.length > 0 ? (
                <div className="space-y-2">
                  {observations.map((obs, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded bg-slate-950/60 border border-slate-800 flex items-start justify-between gap-3 text-xs font-mono"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 font-bold text-slate-100">
                          <span>{obs.title}</span>
                          <CyberBadge
                            label={obs.severity}
                            variant={getSeverityBadgeVariant(obs.severity)}
                            pulse={false}
                          />
                        </div>
                        <p className="text-slate-400">{obs.description}</p>
                      </div>
                      <div className="text-right text-[11px] text-slate-500 shrink-0 font-bold">
                        Conf: {(obs.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="font-mono text-xs text-slate-500">No forensic observations generated.</p>
              )}
            </div>

            {/* Section 4: Structural Validation Issues */}
            <div className="p-4 rounded-lg bg-black/40 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#00E5FF] uppercase border-b border-slate-800 pb-2">
                <ShieldAlert className="w-4 h-4 text-[#00E5FF]" /> Validation Issues ({validation.total_issues || 0})
              </div>

              {validation.issues && validation.issues.length > 0 ? (
                <div className="space-y-2">
                  {validation.issues.map((issue, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded bg-slate-950/40 border border-slate-800 flex items-center justify-between gap-3 text-xs font-mono"
                    >
                      <div className="flex items-center gap-2">
                        <AlertTriangle className={`w-4 h-4 shrink-0 ${issue.severity === 'high' || issue.severity === 'critical' ? 'text-red-400' : 'text-amber-400'}`} />
                        <span className="text-slate-300">{issue.description}</span>
                      </div>
                      <CyberBadge
                        label={issue.type}
                        variant={getSeverityBadgeVariant(issue.severity)}
                        pulse={false}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center gap-2 font-mono text-xs text-emerald-400 pt-1">
                  <CheckCircle2 className="w-4 h-4" /> All structural metadata validation checks passed cleanly.
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
};
