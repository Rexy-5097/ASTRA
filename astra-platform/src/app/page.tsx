'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { MetricCard, Panel } from '@/components/shared/UI';
import { StatusBadge } from '@/components/shared/Badges';
import { useDatasetDetails, useModelDetails } from '@/lib/hooks';
import { AUDIT_EVENTS, CLASS_LABELS, CLASS_COLORS } from '@/lib/data/constants';
import { formatParams, formatPercent } from '@/lib/utils';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { motion, useScroll, useSpring } from 'framer-motion';
import { 
  ChevronDown, 
  ArrowRight, 
  ShieldCheck, 
  Cpu, 
  Database, 
  Compass, 
  Globe, 
  Sparkles, 
  AlertTriangle, 
  Activity, 
  Play, 
  TrendingUp, 
  Search, 
  BarChart2, 
  FileText, 
  CheckCircle2 
} from 'lucide-react';

const sectionNames = [
  { id: 0, tag: '01', title: 'MISSION BRIEFING', desc: 'Objective & Telemetry' },
  { id: 1, tag: '02', title: 'SCIENTIFIC DATASET', desc: 'Stellar Cohorts' },
  { id: 2, tag: '03', title: 'SCIENTIFIC FINDINGS', desc: 'BLS Bottleneck Analysis' },
  { id: 3, tag: '04', title: 'MODEL INTELLIGENCE', desc: 'Neural Core Configurations' },
  { id: 4, tag: '05', title: 'LAUNCH MISSION', desc: 'Operations Control Room' },
];

const sectionVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] as const }
  }
};

const staggerContainer = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.04 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.25, ease: 'easeOut' as const }
  }
};

// Simple animated counter helper
function AnimatedCounter({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const end = value;
    if (start === end) {
      setCount(end);
      return;
    }

    const duration = 1200; // 1.2s
    const stepTime = Math.max(Math.floor(duration / end), 16);
    const stepSize = Math.ceil(end / (duration / stepTime));

    const timer = setInterval(() => {
      start += stepSize;
      if (start >= end) {
        clearInterval(timer);
        setCount(end);
      } else {
        setCount(start);
      }
    }, stepTime);

    return () => clearInterval(timer);
  }, [value]);

  return <span>{count.toLocaleString()}{suffix}</span>;
}

export default function Home() {
  const [health, setHealth] = useState<any>(null);
  const [activeSection, setActiveSection] = useState(0);
  const [mainElement, setMainElement] = useState<HTMLElement | null>(null);
  const mainRef = useRef<HTMLElement | null>(null);

  // Look up scrollable main container at runtime
  useEffect(() => {
    const mainEl = document.querySelector('main');
    if (mainEl instanceof HTMLElement) {
      setMainElement(mainEl);
      mainRef.current = mainEl;
    }
  }, []);

  // Bind scroll progress directly to the main container
  const { scrollYProgress } = useScroll({
    container: mainElement ? { current: mainElement } : undefined
  });

  const scaleX = useSpring(scrollYProgress, {
    stiffness: 120,
    damping: 25,
    restDelta: 0.001
  });

  // Track active section on scroll using IntersectionObserver relative to main element
  useEffect(() => {
    if (!mainElement) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = parseInt(entry.target.getAttribute('data-section-id') || '0');
            setActiveSection(id);
          }
        });
      },
      { 
        root: mainElement,
        threshold: 0.15, 
        rootMargin: '-20% 0px -40% 0px' 
      }
    );

    const elements = document.querySelectorAll('section[data-section-id]');
    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [mainElement]);

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth({ status: 'BLOCKED' }));
  }, []);

  const { data: datasetDetails, isLoading: datasetLoading } = useDatasetDetails();
  const { data: modelDetails, isLoading: modelLoading } = useModelDetails();

  if (datasetLoading || modelLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-[#D7DEE7]">Mission Control</h1>
          <p className="text-[11px] text-[#8B97A7] mt-0.5 animate-pulse font-mono">
            Loading stellar intelligence parameters…
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 astra-glass rounded animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-64 astra-glass rounded animate-pulse" />
          <div className="h-64 astra-glass rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (!datasetDetails || !modelDetails) {
    return (
      <div className="p-6 text-center text-red-400 font-mono border border-red-500/20 bg-red-950/10 rounded">
        System Error: Failed to retrieve dynamic registry configurations. Check API status.
      </div>
    );
  }

  const datasetMetrics = {
    total_stars: datasetDetails.audit.total_stars,
    freeze_date: datasetDetails.audit.generated_at ? datasetDetails.audit.generated_at.slice(0, 10) : '2026-06-12',
    manifest_sha256: datasetDetails.audit.dataset_hash,
    classes: datasetDetails.audit.class_counts,
    period_sources: datasetDetails.audit.period_source_counts,
    splits: datasetDetails.audit.split_counts,
  };

  const modelMetrics = {
    name: modelDetails.checkpoint.filename === 'best_star_transformer_shared.pt' ? 'ASTRA-TRANS-SHARED' : modelDetails.checkpoint.filename.replace('.pt', '').toUpperCase(),
    version: 'v1.0.0',
    architecture: modelDetails.checkpoint.architecture,
    parameters: modelDetails.checkpoint.loaded_params,
    checkpoint_hash: modelDetails.checkpoint.sha256,
    training_date: '2026-06-13',
  };

  const performanceMetrics = {
    val_accuracy: modelDetails.val_accuracy || 0.8582,
    test_accuracy: modelDetails.benchmark.test_accuracy,
    macro_f1: modelDetails.benchmark.macro_f1,
    weighted_f1: modelDetails.benchmark.weighted_f1,
    ece_before: modelDetails.calibration.ece_raw,
    ece_after: modelDetails.calibration.ece_calibrated,
    calibration_temperature: modelDetails.temperature,
  };

  const pieData = Object.entries(datasetMetrics.classes).map(([key, val]) => ({
    name: CLASS_LABELS[key as keyof typeof CLASS_LABELS] || key,
    value: val as number,
    color: CLASS_COLORS[key as keyof typeof CLASS_COLORS] || '#6B7280',
  }));

  const splitData = [
    { name: 'Train', count: datasetMetrics.splits.train, pct: (datasetMetrics.splits.train / datasetMetrics.total_stars) * 100 },
    { name: 'Val', count: datasetMetrics.splits.val, pct: (datasetMetrics.splits.val / datasetMetrics.total_stars) * 100 },
    { name: 'Test', count: datasetMetrics.splits.test, pct: (datasetMetrics.splits.test / datasetMetrics.total_stars) * 100 },
  ];

  const handleScrollToSection = (id: number) => {
    const target = document.getElementById(`section-${id}`);
    const mainEl = mainElement || document.querySelector('main');
    if (target && mainEl) {
      const targetTop = target.getBoundingClientRect().top;
      const mainTop = mainEl.getBoundingClientRect().top;
      const topOffset = targetTop - mainTop + mainEl.scrollTop - 16;
      mainEl.scrollTo({
        top: topOffset,
        behavior: 'smooth'
      });
    }
  };

  return (
    <div className="relative select-text w-full">
      
      {/* Scroll Progress Indicator */}
      <motion.div 
        className="fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-blue-600 via-indigo-500 to-[#6EA8FE] origin-left z-50 shadow-[0_0_8px_rgba(110,168,254,0.4)]" 
        style={{ scaleX }} 
      />

      {/* Side-by-side Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative w-full">
        
        {/* Sticky Sidebar Navigation Indicator */}
        <div className="hidden lg:block lg:col-span-3">
          <div className="sticky top-6 border-l border-white/5 pl-4 py-2 space-y-6 select-none font-mono">
            {sectionNames.map((node) => {
              const isActive = activeSection === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => handleScrollToSection(node.id)}
                  className="group flex flex-col text-left transition-all relative outline-none w-full py-1"
                >
                  {isActive && (
                    <motion.div 
                      layoutId="activeTimelineIndicator"
                      className="absolute left-[-17px] top-1.5 w-1 h-8 rounded-r bg-[#6EA8FE] shadow-[0_0_8px_rgba(110,168,254,0.5)]"
                      transition={{ type: 'spring', stiffness: 220, damping: 24 }}
                    />
                  )}
                  <span className={`text-[10px] leading-none tracking-[0.12em] ${isActive ? 'text-[#6EA8FE] font-bold' : 'text-[#5A6878] group-hover:text-[#8B97A7]'}`}>
                    {node.tag} // {node.title}
                  </span>
                  <span className={`text-[9px] leading-none mt-1.5 ${isActive ? 'text-white/60' : 'text-transparent group-hover:text-white/20'}`}>
                    {node.desc}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Area */}
        <div className="col-span-1 lg:col-span-9 flex flex-col gap-24">

          {/* SECTION 1: MISSION BRIEFING (Hero) */}
          <section 
            id="section-0" 
            data-section-id="0"
            className="min-h-[85vh] flex flex-col justify-center relative py-6"
          >
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-10%' }}
              variants={sectionVariants}
              className="space-y-6"
            >
              <div className="flex items-center gap-2 font-mono">
                <span className="w-2 h-2 rounded-full bg-[#56D364] animate-pulse" />
                <span className="text-[10px] text-[#56D364] tracking-[0.25em] font-bold">
                  SYSTEM STATUS: OPERATIONAL
                </span>
              </div>

              <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight leading-[1.05] text-white">
                ASTRA <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#D7DEE7] via-[#8B97A7] to-[#6EA8FE] text-3xl md:text-5xl font-bold">
                  Stellar Intelligence Platform
                </span>
              </h1>

              <p className="text-[12px] text-[#8B97A7] leading-relaxed max-w-2xl font-mono">
                Aerospace command-grade interface for classifying stellar variability from TESS light curves. 
                Fuses time-series convolutions and self-attention to map orbital morphologies.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl border-t border-white/5 pt-4 text-[10px] font-mono text-[#8B97A7]">
                <div className="flex flex-col gap-1">
                  <span className="text-[#5A6878] text-[9px] tracking-wider uppercase">DATASET LOCK FINGERPRINT</span>
                  <span className="text-white/70 select-all break-all">{datasetMetrics.manifest_sha256}</span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-[#5A6878] text-[9px] tracking-wider uppercase">MODEL CHECKPOINT HASH</span>
                  <span className="text-white/70 select-all break-all">{modelMetrics.checkpoint_hash}</span>
                </div>
              </div>

              <div className="flex items-center gap-4 pt-4">
                <button
                  onClick={() => handleScrollToSection(4)}
                  className="flex items-center gap-2 text-[11px] font-mono px-5 py-2.5 bg-[#1D3A6B]/40 hover:bg-[#1D3A6B] text-white border border-[#6EA8FE]/20 hover:border-[#6EA8FE]/50 rounded transition-all duration-300 shadow-lg"
                >
                  <span>Launch Operations</span>
                  <Play className="w-3.5 h-3.5 fill-current text-[#6EA8FE]" />
                </button>
                <button 
                  onClick={() => handleScrollToSection(1)}
                  className="flex items-center gap-1.5 text-[11px] font-mono text-[#8B97A7] hover:text-[#D7DEE7] transition-colors"
                >
                  <span>Stellar Catalog Data</span>
                  <ChevronDown className="w-3.5 h-3.5 animate-bounce" />
                </button>
              </div>
            </motion.div>

            {/* Zero-Trust Audit Banner */}
            {health && health.status === 'READY' && (
              <motion.div 
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 }}
                className="mt-12 w-full max-w-xl p-3.5 rounded border border-emerald-500/10 bg-emerald-500/5 text-[10px] font-mono flex items-center gap-3 astra-glass"
              >
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                <div className="flex-1">
                  <p className="text-emerald-400 font-bold leading-none uppercase tracking-wider">Zero-Trust Audit Verified</p>
                  <p className="text-white/50 mt-1 leading-tight">Database integrity checks match lineage specifications. Model ONNX signatures verified.</p>
                </div>
              </motion.div>
            )}
          </section>

          {/* SECTION 2: SCIENTIFIC DATASET */}
          <section 
            id="section-1" 
            data-section-id="1"
            className="min-h-[80vh] flex flex-col justify-center py-6 border-t border-white/5"
          >
            <div className="space-y-6">
              <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                <Database className="w-3.5 h-3.5 text-[#6EA8FE]" />
                <span className="uppercase tracking-wider">02 // SCIENTIFIC COHORT SUMMARY</span>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="astra-glass border border-white/5 p-4 rounded font-mono">
                  <span className="text-[#5A6878] text-[9px] uppercase tracking-wider block">Target Cohort</span>
                  <span className="text-2xl font-bold text-white block mt-1">
                    <AnimatedCounter value={944} suffix=" Stars" />
                  </span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">TESS Light Curves</span>
                </div>
                <div className="astra-glass border border-white/5 p-4 rounded font-mono">
                  <span className="text-[#5A6878] text-[9px] uppercase tracking-wider block">Stellar Classes</span>
                  <span className="text-2xl font-bold text-white block mt-1">
                    <AnimatedCounter value={5} suffix=" Classes" />
                  </span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">RR Lyrae, EB, Cep, etc.</span>
                </div>
                <div className="astra-glass border border-white/5 p-4 rounded font-mono">
                  <span className="text-[#5A6878] text-[9px] uppercase tracking-wider block">Catalog Periods</span>
                  <span className="text-2xl font-bold text-white block mt-1">
                    <AnimatedCounter value={597} suffix=" Periods" />
                  </span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">Ground Truth VSX</span>
                </div>
                <div className="astra-glass border border-white/5 p-4 rounded font-mono">
                  <span className="text-[#5A6878] text-[9px] uppercase tracking-wider block">BLS Estimations</span>
                  <span className="text-2xl font-bold text-white block mt-1">
                    <AnimatedCounter value={347} suffix=" Detections" />
                  </span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">Transit Detections</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
                {/* Donut Chart */}
                <Panel title="Class Composition" subtitle="Proportions of stellar classes in the cohort">
                  <div className="h-60 flex flex-col justify-between">
                    <div className="flex-1 min-h-[160px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={75}
                            paddingAngle={2}
                            dataKey="value"
                          >
                            {pieData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              background: '#080C14',
                              border: '1px solid rgba(255, 255, 255, 0.08)',
                              borderRadius: 4,
                              fontSize: 10,
                              fontFamily: 'IBM Plex Mono, monospace',
                              color: '#D7DEE7',
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-3 gap-1.5 mt-2 text-[10px] font-mono">
                      {pieData.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                          <span className="text-[#8B97A7] truncate">{item.name}</span>
                          <span className="text-white/60 ml-auto pr-1">{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </Panel>

                {/* Split Bars */}
                <Panel title="Split Allocation" subtitle="Subdivision of stellar targets for model verification">
                  <div className="h-60 flex flex-col justify-center space-y-4">
                    {splitData.map((item, idx) => (
                      <div key={idx} className="space-y-1.5">
                        <div className="flex items-baseline justify-between text-[11px]">
                          <span className="text-[#D7DEE7] font-medium font-mono">{item.name} Set</span>
                          <div className="space-x-1.5 font-mono text-[10px]">
                            <span className="text-[#8B97A7]">{item.count} targets</span>
                            <span className="text-[#6EA8FE]">{item.pct.toFixed(1)}%</span>
                          </div>
                        </div>
                        <div className="h-1.5 bg-[#1A2430] rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            whileInView={{ width: `${item.pct}%` }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.8, ease: 'easeOut' }}
                            className="h-full rounded-full"
                            style={{
                              backgroundColor: idx === 0 ? '#6EA8FE' : idx === 1 ? '#A78BFA' : '#F59E0B',
                            }}
                          />
                        </div>
                      </div>
                    ))}
                    <div className="text-[9px] text-[#5A6878] leading-normal bg-black/35 p-3 rounded border border-white/5 font-mono mt-2">
                      Allocation is strictly isolated via deterministic hash keys to ensure zero target/validation leakage.
                    </div>
                  </div>
                </Panel>
              </div>
            </div>
          </section>

          {/* SECTION 3: SCIENTIFIC FINDINGS */}
          <section 
            id="section-2" 
            data-section-id="2"
            className="min-h-[80vh] flex flex-col justify-center py-6 border-t border-white/5"
          >
            <div className="space-y-6">
              <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                <TrendingUp className="w-3.5 h-3.5 text-[#F59E0B]" />
                <span className="uppercase tracking-wider">03 // BOTTLENECK INVESTIGATION</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
                <div className="md:col-span-7 space-y-4">
                  <h2 className="text-2xl font-bold text-white tracking-tight">
                    BLS Period Mismatch <br />
                    <span className="text-[#F59E0B]">The Core Classification Bottleneck</span>
                  </h2>
                  <p className="text-[11px] text-[#8B97A7] leading-relaxed font-mono">
                    Audit reports show that **BLS-derived period estimations represent the primary bottleneck** in classification accuracy. 
                    Due to short TESS observation baselines, the Box Least Squares (BLS) search is prone to harmonic and sub-harmonic period aliasing.
                  </p>
                  
                  <div className="bg-[#78350F]/5 border border-[#78350F]/20 p-3.5 rounded text-[10px] font-mono text-[#D7DEE7] leading-relaxed">
                    <div className="flex items-center gap-2 text-amber-500 font-bold mb-1.5">
                      <AlertTriangle className="w-4 h-4" />
                      <span>BLS ACCURACY REDUCTION</span>
                    </div>
                    variable targets with incorrect BLS periods suffer an accuracy drop of over 30%, showing severe sensitivity to period estimation quality.
                  </div>
                </div>

                <div className="md:col-span-5 astra-glass border border-white/5 p-5 rounded space-y-5 font-mono">
                  <h3 className="text-[11px] font-bold text-white uppercase tracking-wider border-b border-white/5 pb-2">
                    Classification Accuracy Comparison
                  </h3>

                  {/* Accuracy bars */}
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px]">
                        <span className="text-[#56D364] font-semibold">Non-BLS Targets (Correct Period)</span>
                        <span className="text-white">90.3%</span>
                      </div>
                      <div className="h-2 bg-[#1A2430] rounded-full overflow-hidden">
                        <div className="h-full bg-[#56D364] rounded-full w-[90.3%]" />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px]">
                        <span className="text-[#D29922] font-semibold">BLS-Dependent Targets</span>
                        <span className="text-white">58.2%</span>
                      </div>
                      <div className="h-2 bg-[#1A2430] rounded-full overflow-hidden">
                        <div className="h-full bg-[#D29922] rounded-full w-[58.2%]" />
                      </div>
                    </div>
                  </div>

                  <p className="text-[9px] text-[#5A6878] leading-tight">
                    *Source: Verified Phase 7C audit reports and coordinate validation files.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* SECTION 4: MODEL INTELLIGENCE */}
          <section 
            id="section-3" 
            data-section-id="3"
            className="min-h-[80vh] flex flex-col justify-center py-6 border-t border-white/5"
          >
            <div className="space-y-6">
              <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                <Cpu className="w-3.5 h-3.5 text-[#6EA8FE]" />
                <span className="uppercase tracking-wider">04 // NEURAL BACKBONE</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                
                {/* Left Column - Specs */}
                <div className="md:col-span-5 astra-glass border border-white/5 p-4 rounded font-mono space-y-4">
                  <div className="border-b border-white/5 pb-2 flex justify-between items-center text-[10px]">
                    <span className="text-[#D7DEE7] font-bold">NEURAL NETWORKS CONFIG</span>
                    <span className="text-[#6EA8FE] uppercase font-bold tracking-widest text-[9px]">LOCKED</span>
                  </div>

                  <div className="space-y-3.5 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-[#8B97A7]">Model Tag:</span>
                      <span className="text-white font-bold">{modelMetrics.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B97A7]">Transformer Core:</span>
                      <span className="text-[#6EA8FE]">4 Layers, 8 Heads</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B97A7]">CNN Backbone:</span>
                      <span className="text-[#6EA8FE]">Dual-Branch 1D-Conv</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B97A7]">Transformer Params:</span>
                      <span className="text-white">{formatParams(1373701)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B97A7]">CNN Branch Params:</span>
                      <span className="text-white">{formatParams(1043333)}</span>
                    </div>
                  </div>
                </div>

                {/* Right Column - Stats */}
                <div className="md:col-span-7 astra-glass border border-white/5 p-4 rounded font-mono space-y-4">
                  <div className="border-b border-white/5 pb-2 flex justify-between items-center text-[10px]">
                    <span className="text-[#D7DEE7] font-bold">CALIBRATION &amp; UNCERTAINTY DIAGNOSTICS</span>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-black/20 border border-white/5 rounded">
                      <span className="text-[9px] text-[#5A6878] uppercase block">ECE (Uncalibrated)</span>
                      <span className="text-lg font-bold text-amber-500 block mt-1">
                        {performanceMetrics.ece_before.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[#8B97A7]">Significant overconfidence</span>
                    </div>
                    <div className="p-3 bg-black/20 border border-white/5 rounded">
                      <span className="text-[9px] text-[#5A6878] uppercase block">ECE (Calibrated)</span>
                      <span className="text-lg font-bold text-emerald-400 block mt-1">
                        {performanceMetrics.ece_after.toFixed(4)}
                      </span>
                      <span className="text-[9px] text-[#8B97A7]">T={performanceMetrics.calibration_temperature.toFixed(3)} temperature scaling</span>
                    </div>
                  </div>

                  <div className="text-[10px] text-[#8B97A7] leading-relaxed bg-[#05070B]/50 p-2.5 rounded border border-white/5">
                    <strong>Uncertainty Filtering:</strong> Applying entropy thresholding to isolate low-confidence predictions enables a target error rate below 5% for high-certainty subsets, proving the value of calibration.
                  </div>
                </div>

              </div>
            </div>
          </section>

          {/* SECTION 5: LAUNCH MISSION */}
          <section 
            id="section-4" 
            data-section-id="4"
            className="py-6 border-t border-white/5 space-y-6"
          >
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                <Activity className="w-3.5 h-3.5 text-[#6EA8FE]" />
                <span className="uppercase tracking-wider">05 // MISSION OPERATIONS</span>
              </div>
              <h2 className="text-3xl font-bold text-white tracking-tight">
                Operations Command Room
              </h2>
              <p className="text-[11px] text-[#8B97A7] max-w-xl font-mono">
                De-mute audio controls, set GFX settings, and launch workspace dashboards to explore light curve targets.
              </p>
            </div>

            {/* Launch Dashboards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
              
              <Link 
                href="/search"
                className="group p-4 rounded border border-white/5 hover:border-[#6EA8FE]/30 astra-glass hover:bg-[#1D3A6B]/10 transition-all duration-300 flex flex-col justify-between h-36 font-mono text-left"
              >
                <div className="flex justify-between items-center text-[#8B97A7] group-hover:text-[#6EA8FE]">
                  <Search className="w-5 h-5" />
                  <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                </div>
                <div className="mt-4">
                  <span className="text-white font-bold block text-[13px]">Target Search</span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">Search 944 variable stars</span>
                </div>
              </Link>

              <Link 
                href="/analysis"
                className="group p-4 rounded border border-white/5 hover:border-[#6EA8FE]/30 astra-glass hover:bg-[#1D3A6B]/10 transition-all duration-300 flex flex-col justify-between h-36 font-mono text-left"
              >
                <div className="flex justify-between items-center text-[#8B97A7] group-hover:text-[#6EA8FE]">
                  <BarChart2 className="w-5 h-5" />
                  <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                </div>
                <div className="mt-4">
                  <span className="text-white font-bold block text-[13px]">Curve Analysis</span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">Folded &amp; raw light curves</span>
                </div>
              </Link>

              <Link 
                href="/research"
                className="group p-4 rounded border border-white/5 hover:border-[#6EA8FE]/30 astra-glass hover:bg-[#1D3A6B]/10 transition-all duration-300 flex flex-col justify-between h-36 font-mono text-left"
              >
                <div className="flex justify-between items-center text-[#8B97A7] group-hover:text-[#6EA8FE]">
                  <FileText className="w-5 h-5" />
                  <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                </div>
                <div className="mt-4">
                  <span className="text-white font-bold block text-[13px]">Research Mode</span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">Scientific audits &amp; papers</span>
                </div>
              </Link>

              <Link 
                href="/osint"
                className="group p-4 rounded border border-white/5 hover:border-[#6EA8FE]/30 astra-glass hover:bg-[#1D3A6B]/10 transition-all duration-300 flex flex-col justify-between h-36 font-mono text-left"
              >
                <div className="flex justify-between items-center text-[#8B97A7] group-hover:text-[#6EA8FE]">
                  <Globe className="w-5 h-5" />
                  <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                </div>
                <div className="mt-4">
                  <span className="text-white font-bold block text-[13px]">Space OSINT</span>
                  <span className="text-[10px] text-[#8B97A7] mt-0.5 block">Live satellite metadata feeds</span>
                </div>
              </Link>

            </div>

            {/* Audit log table in Launch section */}
            <div className="pt-8">
              <Panel title="Mission Milestones" subtitle="Verified project gate releases and audits">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-[11px] text-[#D7DEE7]">
                    <thead>
                      <tr className="border-b border-white/5">
                        <th className="py-2 font-medium text-[#8B97A7] uppercase tracking-wider w-16">Phase</th>
                        <th className="py-2 font-medium text-[#8B97A7] uppercase tracking-wider">Gate Title</th>
                        <th className="py-2 font-medium text-[#8B97A7] uppercase tracking-wider w-20">Date</th>
                        <th className="py-2 font-medium text-[#8B97A7] uppercase tracking-wider w-16 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 font-mono">
                      {AUDIT_EVENTS.slice(-3).map((evt, idx) => (
                        <tr key={idx} className="hover:bg-white/5">
                          <td className="py-2.5 text-[#6EA8FE] font-bold">{evt.phase}</td>
                          <td className="py-2.5 font-sans font-medium text-[#D7DEE7]">{evt.title}</td>
                          <td className="py-2.5 text-[#8B97A7]">{evt.date}</td>
                          <td className="py-2.5 text-right">
                            <StatusBadge status={evt.status as 'PASS'} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </div>

            {/* Cryptographic Footer */}
            <div className="flex justify-between items-center text-[9px] text-[#5A6878] font-mono py-2 border-t border-white/5 select-none pt-4">
              <span>DATASET_MANIFEST_SHA256: {datasetMetrics.manifest_sha256}</span>
              <span>MODEL_CHECKPOINT_SHA256: {modelMetrics.checkpoint_hash}</span>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
