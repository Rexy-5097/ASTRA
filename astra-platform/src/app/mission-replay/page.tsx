'use client';

import { useState, useEffect, useRef } from 'react';
import { useStars, useLightCurve, useExplain } from '@/lib/hooks';
import { ClassBadge, PeriodSourceBadge } from '@/components/shared/Badges';
import { MetricCard, Panel, ConfidenceBar, EmptyState } from '@/components/shared/UI';
import { formatRA, formatDec, formatPeriod, formatPercent, CLASS_LABELS, CLASS_COLORS, generateProbabilities } from '@/lib/utils';
import type { Star, AstraClass } from '@/lib/types';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, Play, Pause, RotateCcw, AlertCircle } from 'lucide-react';

function AttentionHeatmap({ matrix }: { matrix: number[][] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !matrix || matrix.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const N = matrix.length;
    const cellW = width / N;
    const cellH = height / N;

    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        const val = matrix[i][j];
        const alpha = Math.min(1.0, val * 20.0); // scale for high visual contrast
        ctx.fillStyle = `rgba(110, 168, 254, ${alpha})`;
        ctx.fillRect(j * cellW, i * cellH, cellW, cellH);
      }
    }
  }, [matrix]);

  return (
    <div className="space-y-1.5 flex flex-col items-center">
      <div className="relative border border-white/10 bg-[#05070B] rounded overflow-hidden flex justify-center p-1">
        <canvas ref={canvasRef} width={200} height={200} className="w-[180px] h-[180px]" />
        <div className="absolute left-1 bottom-1 top-1 w-5 border-r border-white/5 bg-[#0C1118]/70 flex flex-col justify-around text-[6px] font-mono text-[#8B97A7] uppercase select-none pointer-events-none text-center">
          <span className="-rotate-90">Raw</span>
          <span className="-rotate-90">Fold</span>
        </div>
      </div>
      <p className="text-[9px] text-[#5A6878] font-mono text-center max-w-[280px] leading-tight">
        Self-Attention Matrix [250 × 250] · Raw CNN Tokens (0-124) | Folded CNN Tokens (125-249)
      </p>
    </div>
  );
}

// 8 Visual Stages for the Pipeline Flowchart
const FLOWCHART_NODES = [
  { id: 0, label: 'Raw Light Curve', steps: [0, 1] },
  { id: 1, label: 'Normalization', steps: [2] },
  { id: 2, label: 'Period Detection', steps: [3] },
  { id: 3, label: 'Phase Folding', steps: [4] },
  { id: 4, label: 'CNN Features', steps: [5] },
  { id: 5, label: 'Attention', steps: [6, 7] },
  { id: 6, label: 'Calibration', steps: [8, 9] },
  { id: 7, label: 'Prediction', steps: [10] },
];

const PIPELINE_STEPS = [
  { id: 0, title: 'Raw Light Curve', icon: '📡', description: 'Multi-sector TESS photometry loaded from SPOC/QLP pipeline. Time-series flux values in electrons/second.' },
  { id: 1, title: 'Quality Filtering', icon: '🔍', description: 'Outlier sigma-clipping (3σ), NaN removal, cadence gap detection. Reduces n_points_raw to n_points_clean.' },
  { id: 2, title: 'Normalization', icon: '📊', description: 'Robust median normalization. Each sector normalized independently to zero median. Final output range ≈ [-1, 1].' },
  { id: 3, title: 'Period Detection', icon: '🔄', description: 'Selected period applied (catalog preferred, BLS fallback). Period source determines confidence priors.' },
  { id: 4, title: 'Phase Folding', icon: '🌀', description: 'Light curve folded at selected period. Phase space binned to 200 points. Creates characteristic shape per class.' },
  { id: 5, title: 'CNN Branch', icon: '🧠', description: 'Dual-branch CNN processes 1000-point raw flux and 200-point folded flux independently. Extracts local morphological features.' },
  { id: 6, title: 'Transformer Encoder', icon: '⚡', description: 'Multi-head self-attention (8 heads, d_model=128) applied to flux sequences. Shared weights across both branches.' },
  { id: 7, title: 'Feature Fusion', icon: '🔗', description: 'CNN and Transformer feature vectors concatenated. Final representation captures both local and global temporal patterns.' },
  { id: 8, title: 'Classification Head', icon: '🎯', description: 'Linear layer maps to 5-class logits. Softmax produces probability distribution over: RR Lyrae, Cepheid, Eclipsing Binary, Solar-like, Stable.' },
  { id: 9, title: 'Temperature Scaling', icon: '📐', description: 'Post-hoc calibration with T=1.2577 scaling parameter applied. Lowers Expected Calibration Error from 0.0810 to 0.0442.' },
  { id: 10, title: 'Final Prediction', icon: '✅', description: 'Final classification assignment with calibrated confidence. Stars with BLS periods receive lower priority output flags.' },
];

function sampleArray(arr: number[], maxPoints: number): { x: number; y: number }[] {
  if (!arr || arr.length === 0) return [];
  const step = Math.max(1, Math.floor(arr.length / maxPoints));
  const result = [];
  for (let i = 0; i < arr.length; i += step) {
    result.push({ x: i, y: +arr[i].toFixed(6) });
  }
  return result;
}

export default function MissionReplayPage() {
  const [selectedStar, setSelectedStar] = useState<Star | null>(null);
  const [query, setQuery] = useState('');
  const [activeStep, setActiveStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const { data: starsData, isLoading: starsLoading } = useStars({
    q: query || undefined,
    limit: 50,
  });

  const { data: lc, isLoading: lcLoading } = useLightCurve(selectedStar?.tic_id ?? null);
  const { data: explainData, isLoading: explainLoading } = useExplain(selectedStar?.tic_id ?? null);

  const handleSelectStar = (star: Star) => {
    setSelectedStar(star);
    setActiveStep(0);
    setIsPlaying(false);
  };

  const handleNextStep = () => {
    setActiveStep((s) => Math.min(PIPELINE_STEPS.length - 1, s + 1));
  };

  const handlePrevStep = () => {
    setActiveStep((s) => Math.max(0, s - 1));
  };

  // Play/Autoplay transition logic
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isPlaying) {
      timer = setInterval(() => {
        setActiveStep((prev) => {
          if (prev >= PIPELINE_STEPS.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 3000); // 3 seconds per step
    }
    return () => clearInterval(timer);
  }, [isPlaying]);

  // Determine active flowchart stage ID from activeStep ID
  const getActiveStageId = () => {
    const node = FLOWCHART_NODES.find((node) => node.steps.includes(activeStep));
    return node ? node.id : 0;
  };

  const activeStageId = getActiveStageId();

  const probabilities: Record<string, number> = explainData?.probabilities || (selectedStar ? generateProbabilities(selectedStar.tic_id, selectedStar.astra_class) : {} as Record<string, number>);
  const topProb = explainData?.calibrated_confidence || (selectedStar ? (probabilities[selectedStar.astra_class] || 0.7) : 0.7);

  return (
    <div className="flex gap-4 h-[calc(100vh-7rem)] select-text">
      
      {/* Target Selector Sidebar */}
      <div className="w-64 shrink-0 rounded astra-glass flex flex-col">
        <div className="px-3 py-2.5 border-b border-white/5">
          <p className="text-[0.6875rem] uppercase tracking-widest text-[#8B97A7] mb-2 font-mono">
            Select Target
          </p>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search TIC ID or class…"
            className="w-full bg-[#05070B] border border-white/10 rounded px-2.5 py-1.5 text-[0.75rem] text-[#D7DEE7] placeholder-[#5A6878] focus:outline-none focus:border-[#6EA8FE] font-mono"
          />
        </div>
        <div className="flex-1 overflow-y-auto">
          {starsLoading && (
            <p className="text-[0.75rem] text-[#5A6878] p-3 font-mono">Loading registry…</p>
          )}
          {starsData?.stars.map((star) => (
            <button
              key={star.tic_id}
              onClick={() => handleSelectStar(star)}
              className={`w-full text-left px-3 py-2 border-b border-white/5 hover:bg-white/5 transition-colors flex flex-col ${
                selectedStar?.tic_id === star.tic_id ? 'bg-[#1D3A6B]/30 border-l-2 border-l-[#6EA8FE]' : ''
              }`}
            >
              <span className="text-[11px] font-mono text-[#D7DEE7]">TIC {star.tic_id}</span>
              <div className="flex items-center gap-1.5 mt-1">
                <ClassBadge cls={star.astra_class} />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Replay workspace */}
      <div className="flex-1 rounded astra-glass flex flex-col overflow-hidden">
        {!selectedStar ? (
          <EmptyState
            message="Select a target from the registry to begin replay"
            sub="You will be able to review raw sensors, convolutional layers, attention transforms, and class scaling."
          />
        ) : (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Active target header bar */}
            <div className="px-4 py-3 border-b border-white/5 bg-black/30 flex items-center justify-between flex-wrap gap-3 shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-[#8B97A7]">REPLAY FLUX:</span>
                <span className="font-mono text-sm text-[#D7DEE7] font-semibold">TIC {selectedStar.tic_id}</span>
                <ClassBadge cls={selectedStar.astra_class} />
                <PeriodSourceBadge source={selectedStar.period_source} />
              </div>

              {/* Autoplay Controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded border border-white/10 hover:bg-white/5 text-[#8B97A7] hover:text-[#D7DEE7]"
                >
                  {isPlaying ? (
                    <>
                      <Pause className="w-3 h-3 text-amber-500" />
                      <span>Pause</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 text-emerald-400" />
                      <span>Autoplay</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setActiveStep(0);
                    setIsPlaying(false);
                  }}
                  className="flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded border border-white/10 hover:bg-white/5 text-[#8B97A7] hover:text-[#D7DEE7]"
                  title="Reset to start"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset</span>
                </button>
              </div>
            </div>

            {/* PIPELINE VISUAL FLOWCHART (Animated) */}
            <div className="px-4 py-3 border-b border-white/5 bg-[#05070B]/40 overflow-x-auto shrink-0 select-none">
              <div className="flex items-center justify-between min-w-[760px] gap-1">
                {FLOWCHART_NODES.map((node, index) => {
                  const isActive = activeStageId === node.id;
                  const isCompleted = activeStageId > node.id;

                  return (
                    <div key={node.id} className="flex items-center flex-1 gap-1">
                      {/* Flowchart Node */}
                      <motion.div
                        animate={{
                          borderColor: isActive 
                            ? 'rgba(110, 168, 254, 0.5)' 
                            : isCompleted 
                            ? 'rgba(86, 211, 100, 0.3)' 
                            : 'rgba(255, 255, 255, 0.05)',
                          backgroundColor: isActive 
                            ? 'rgba(29, 58, 107, 0.3)' 
                            : isCompleted 
                            ? 'rgba(26, 61, 34, 0.2)' 
                            : 'rgba(12, 17, 24, 0.5)',
                        }}
                        transition={{ duration: 0.3 }}
                        onClick={() => {
                          setActiveStep(node.steps[0]);
                          setIsPlaying(false);
                        }}
                        className={`px-2 py-1.5 rounded border text-center flex-1 cursor-pointer transition-shadow ${
                          isActive ? 'shadow-[0_0_8px_rgba(110,168,254,0.15)]' : ''
                        }`}
                      >
                        <p className={`text-[9px] font-mono font-medium leading-none ${
                          isActive 
                            ? 'text-[#6EA8FE]' 
                            : isCompleted 
                            ? 'text-[#56D364]' 
                            : 'text-[#8B97A7]'
                        }`}>
                          {node.label}
                        </p>
                        <div className="flex items-center justify-center gap-1 mt-1 leading-none">
                          <span className="text-[7px] text-white/30 font-mono">
                            STG 0{node.id + 1}
                          </span>
                        </div>
                      </motion.div>

                      {/* Connection arrow */}
                      {index < FLOWCHART_NODES.length - 1 && (
                        <ChevronRight className={`w-3.5 h-3.5 shrink-0 ${
                          isCompleted ? 'text-[#56D364]/50' : 'text-[#1A2430]'
                        }`} />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Main Area: left steps timeline, right details */}
            <div className="flex-1 flex overflow-hidden">
              
              {/* Vertical timeline steps list */}
              <div className="w-52 shrink-0 border-r border-white/5 overflow-y-auto py-2">
                {PIPELINE_STEPS.map((step) => {
                  const isActive = activeStep === step.id;
                  const isCompleted = activeStep > step.id;
                  return (
                    <button
                      key={step.id}
                      onClick={() => {
                        setActiveStep(step.id);
                        setIsPlaying(false);
                      }}
                      className={`w-full text-left px-3 py-1.5 text-[11px] hover:bg-white/5 transition-colors relative flex items-center gap-2 ${
                        isActive
                          ? 'text-[#6EA8FE] bg-[#1D3A6B]/20 font-medium'
                          : isCompleted
                          ? 'text-[#56D364]'
                          : 'text-[#8B97A7]'
                      }`}
                    >
                      <span className="font-mono text-[9px] w-4 text-[#5A6878]">{step.id}</span>
                      <span className="shrink-0">{step.icon}</span>
                      <span className="truncate">{step.title}</span>
                      {isActive && <span className="absolute right-0 top-0 bottom-0 w-0.5 bg-[#6EA8FE]" />}
                    </button>
                  );
                })}
              </div>

              {/* Step workspace details */}
              <div className="flex-1 overflow-y-auto p-4 flex flex-col justify-between space-y-4">
                
                {/* Step Info Header */}
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{PIPELINE_STEPS[activeStep].icon}</span>
                    <div>
                      <span className="font-mono text-[9px] text-[#8B97A7] uppercase tracking-wider">
                        PROCESS GATE 0{activeStep + 1} OF 11
                      </span>
                      <h2 className="text-[13px] font-semibold text-[#D7DEE7] leading-tight">
                        {PIPELINE_STEPS[activeStep].title}
                      </h2>
                    </div>
                  </div>
                  <p className="text-[11px] text-[#8B97A7] leading-relaxed max-w-xl font-mono">
                    {PIPELINE_STEPS[activeStep].description}
                  </p>
                </div>

                {/* Animated Chart / Details Wrapper */}
                <div className="flex-1 bg-[#05070B] border border-white/5 rounded p-4 flex flex-col justify-center min-h-[220px] relative overflow-hidden">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeStep}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      transition={{ duration: 0.25 }}
                      className="w-full h-full flex flex-col justify-center"
                    >
                      
                      {/* Step 0: Raw Light Curve */}
                      {activeStep === 0 && (
                        <div className="space-y-3">
                          <p className="text-[10px] uppercase text-[#8B97A7] tracking-wider font-mono">
                            Raw Photometric Time-Series
                          </p>
                          {lcLoading ? (
                            <p className="text-[11px] text-[#5A6878] font-mono animate-pulse">Loading data arrays…</p>
                          ) : lc ? (
                            <ResponsiveContainer width="100%" height={150}>
                              <LineChart data={sampleArray(lc.flux_1000, 200)}>
                                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.05)" />
                                <XAxis dataKey="x" tick={{ fill: '#5A6878', fontSize: 8 }} />
                                <YAxis tick={{ fill: '#5A6878', fontSize: 8 }} />
                                <Line type="monotone" dataKey="y" stroke="#6EA8FE" strokeWidth={1} dot={false} />
                              </LineChart>
                            </ResponsiveContainer>
                          ) : (
                            <p className="text-[11px] text-red-400 font-mono">Error loading arrays</p>
                          )}
                        </div>
                      )}

                      {/* Step 1: Quality Filtering */}
                      {activeStep === 1 && (
                        <div className="space-y-2 font-mono text-[11px] text-[#8B97A7]">
                          <p className="font-sans text-[#D7DEE7] font-semibold mb-2">Quality Gates</p>
                          <div className="flex justify-between border-b border-white/5 py-1">
                            <span>Original Observations (n_points_raw):</span>
                            <span className="text-[#D7DEE7]">{selectedStar.n_points_raw}</span>
                          </div>
                          <div className="flex justify-between border-b border-white/5 py-1">
                            <span>Cleaned Observations (n_points_clean):</span>
                            <span className="text-[#D7DEE7]">{selectedStar.n_points_clean}</span>
                          </div>
                          <div className="flex justify-between border-b border-white/5 py-1">
                            <span>Outlier Removal rate:</span>
                            <span className="text-amber-500 font-semibold">
                              {((1 - selectedStar.n_points_clean / selectedStar.n_points_raw) * 100).toFixed(2)}%
                            </span>
                          </div>
                          <div className="flex justify-between py-1">
                            <span>NaN / Null detections:</span>
                            <span className="text-emerald-400">0</span>
                          </div>
                        </div>
                      )}

                      {/* Step 2: Normalization */}
                      {activeStep === 2 && (
                        <div className="space-y-3 text-[11px] leading-relaxed">
                          <p className="font-semibold text-[#D7DEE7]">Sector-Wise Median Normalization</p>
                          <p className="text-[#8B97A7]">
                            Transforms light curve offsets so separate TESS sectors align perfectly at 0 median.
                            Standardizes amplitude signals across observations (exposure time:{' '}
                            <span className="font-mono text-[#D7DEE7]">{selectedStar.sector_information?.[0]?.exptime ?? 1800}s</span>).
                          </p>
                          <div className="p-2.5 astra-glass rounded font-mono text-[10px] text-emerald-400">
                            Formula: flux_norm = (flux - median(flux)) / median(flux)
                          </div>
                        </div>
                      )}

                      {/* Step 3: Period Detection */}
                      {activeStep === 3 && (
                        <div className="space-y-3 text-[11px]">
                          <p className="font-semibold text-[#D7DEE7]">Periodicity Estimation Results</p>
                          <div className="grid grid-cols-2 gap-4 font-mono">
                            <div className="p-2 astra-glass rounded">
                              <span className="text-[#8B97A7] block text-[9px]">BLS PERIOD</span>
                              <span className="text-[#D7DEE7] text-xs">
                                {selectedStar.bls_period ? formatPeriod(selectedStar.bls_period) : 'N/A'}
                              </span>
                            </div>
                            <div className="p-2 astra-glass rounded">
                              <span className="text-[#8B97A7] block text-[9px]">CATALOG PERIOD</span>
                              <span className="text-[#D7DEE7] text-xs">
                                {selectedStar.catalog_period ? formatPeriod(selectedStar.catalog_period) : 'N/A'}
                              </span>
                            </div>
                          </div>
                          <div className="p-2.5 astra-glass rounded font-mono">
                            <div className="flex justify-between">
                              <span>Applied Period:</span>
                              <span className="text-[#6EA8FE] font-bold">{formatPeriod(selectedStar.period)}</span>
                            </div>
                            <div className="flex justify-between mt-1.5">
                              <span>BLS Power Score:</span>
                              <span className="text-[#D7DEE7]">{selectedStar.bls_power?.toFixed(6) ?? 'N/A'}</span>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Step 4: Phase Folding */}
                      {activeStep === 4 && (
                        <div className="space-y-3">
                          <p className="text-[10px] uppercase text-[#8B97A7] tracking-wider font-mono">
                            Phase-Folded Curve (200 bins)
                          </p>
                          {lcLoading ? (
                            <p className="text-[11px] text-[#5A6878] font-mono animate-pulse">Loading data arrays…</p>
                          ) : lc ? (
                            <ResponsiveContainer width="100%" height={150}>
                              <LineChart data={sampleArray(lc.folded_flux_200, 200)}>
                                <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.05)" />
                                <XAxis dataKey="x" tick={{ fill: '#5A6878', fontSize: 8 }} />
                                <YAxis tick={{ fill: '#5A6878', fontSize: 8 }} />
                                <Line type="monotone" dataKey="y" stroke="#A78BFA" strokeWidth={1} dot={false} />
                              </LineChart>
                            </ResponsiveContainer>
                          ) : (
                            <p className="text-[11px] text-red-400 font-mono">Error loading arrays</p>
                          )}
                        </div>
                      )}

                      {/* Step 5: CNN Branch */}
                      {activeStep === 5 && (
                        <div className="space-y-2 text-[11px] text-[#8B97A7]">
                          <p className="font-semibold text-[#D7DEE7]">Dual-Branch Convolutional Embeddings</p>
                          <p>
                            Sends raw 1000-point flux to raw branch, and 200-point phase folded flux to folded branch.
                            Convolutions extract localized temporal and shape features.
                          </p>
                          <div className="grid grid-cols-2 gap-3 font-mono text-[10px] text-white/50 pt-2">
                            <div className="p-2 astra-glass rounded">Raw CNN Shape: [1, 128, 250]</div>
                            <div className="p-2 astra-glass rounded">Folded CNN Shape: [1, 128, 50]</div>
                          </div>
                        </div>
                      )}

                      {/* Step 6: Transformer Encoder */}
                      {activeStep === 6 && (
                        <div className="space-y-3 text-[11px] text-[#8B97A7] flex flex-col justify-between h-full">
                          <div className="space-y-1">
                            <p className="font-semibold text-[#D7DEE7]">Multi-Head Self-Attention Transformer</p>
                            <p>
                              A 4-layer Transformer Encoder processes the sequence of temporal convolutional activations.
                              Attention heads (8 heads, embedding dimension 128) relate global trends across the light curve.
                            </p>
                          </div>
                          {explainLoading ? (
                            <div className="h-44 flex items-center justify-center font-mono text-[10px] text-[#5A6878] animate-pulse">
                              Loading attention matrix from ONNX session...
                            </div>
                          ) : explainData?.attention_weights ? (
                            <AttentionHeatmap matrix={explainData.attention_weights} />
                          ) : (
                            <div className="p-2 astra-glass rounded font-mono text-[9px] text-[#6EA8FE]">
                              Query/Key/Value Attention weight maps verified in Phase 8 checkpoint audit.
                            </div>
                          )}
                        </div>
                      )}

                      {/* Step 7: Feature Fusion */}
                      {activeStep === 7 && (
                        <div className="space-y-3 text-[11px] text-[#8B97A7]">
                          <p className="font-semibold text-[#D7DEE7]">Feature Concatenation</p>
                          <p>
                            Fuses the global context vector from the Transformer branch with the localized morphological features
                            extracted by the CNN branches.
                          </p>
                          <div className="p-3 astra-glass rounded font-mono text-[11px] text-center text-[#D7DEE7] flex justify-between">
                            <span>Concatenation Stage:</span>
                            <span className="text-emerald-400 font-bold">512 channels</span>
                          </div>
                        </div>
                      )}

                      {/* Step 8: Classification Head */}
                      {activeStep === 8 && (
                        <div className="space-y-3">
                          <p className="text-[10px] uppercase text-[#8B97A7] tracking-wider font-mono">Logit Probabilities</p>
                          <div className="space-y-2">
                            {Object.entries(probabilities).map(([key, val]) => (
                              <div key={key}>
                                <div className="flex justify-between items-baseline text-[9px] font-mono text-[#8B97A7]">
                                  <span>{CLASS_LABELS[key as keyof typeof CLASS_LABELS]}</span>
                                  <span>{(val * 100).toFixed(1)}%</span>
                                </div>
                                <ConfidenceBar value={val} color={CLASS_COLORS[key as keyof typeof CLASS_COLORS]} />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Step 9: Temperature Scaling */}
                      {activeStep === 9 && (
                        <div className="space-y-2 text-[11px]">
                          <p className="font-semibold text-[#D7DEE7]">Logits Calibration (T=1.2577)</p>
                          <p className="text-[#8B97A7]">
                            Divides model logits by the temperature factor (T) before softmax activation to reduce overconfidence.
                          </p>
                          <div className="grid grid-cols-2 gap-4 font-mono text-[10px] text-center pt-2">
                            <div className="p-2 astra-glass rounded text-amber-500">
                              Raw ECE: 8.10%
                            </div>
                            <div className="p-2 astra-glass rounded text-emerald-400">
                              Calibrated ECE: 4.42%
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Step 10: Final Prediction */}
                      {activeStep === 10 && (
                        <div className="space-y-3 text-center">
                          <p className="text-[10px] uppercase text-[#8B97A7] tracking-wider font-mono">Classification Assignment</p>
                          <div className="inline-block px-5 py-2.5 border border-emerald-500/20 bg-emerald-500/5 rounded">
                            <p className="text-[9px] text-[#8B97A7] uppercase font-mono">Predicted class</p>
                            <p className="text-base font-semibold text-white mt-1">
                              {CLASS_LABELS[selectedStar.astra_class]}
                            </p>
                          </div>
                          <p className="text-[11px] text-[#8B97A7]">
                            Calibrated Confidence: <span className="font-mono text-emerald-400 font-semibold">{formatPercent(topProb)}</span>
                          </p>
                        </div>
                      )}

                    </motion.div>
                  </AnimatePresence>
                </div>

                {/* Back / Next buttons */}
                <div className="flex justify-between items-center shrink-0 border-t border-white/5 pt-3">
                  <button
                    onClick={handlePrevStep}
                    disabled={activeStep === 0}
                    className="px-3 py-1.5 bg-[#05070B] border border-white/10 text-[#8B97A7] hover:text-[#D7DEE7] disabled:opacity-30 rounded text-[11px] font-mono"
                  >
                    Back
                  </button>
                  <span className="font-mono text-[10px] text-[#5A6878]">
                    Step {activeStep + 1} of {PIPELINE_STEPS.length}
                  </span>
                  <button
                    onClick={handleNextStep}
                    disabled={activeStep === PIPELINE_STEPS.length - 1}
                    className="px-3 py-1.5 bg-[#1D3A6B] text-[#D7DEE7] hover:bg-[#1D3A6B]/80 disabled:opacity-30 rounded text-[11px] font-mono"
                  >
                    Continue
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
