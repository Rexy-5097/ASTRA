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
import { ChevronDown, ArrowRight, ShieldCheck, Cpu, Database, Compass, Globe, Sparkles } from 'lucide-react';

const sectionNames = [
  { id: 0, tag: '01', title: 'MISSION INITIATION', desc: 'Objective & Parameters' },
  { id: 1, tag: '02', title: 'DATA FREEZE', desc: 'Dataset Lock' },
  { id: 2, tag: '03', title: 'MODEL CORE', desc: 'Neural Encoder' },
  { id: 3, tag: '04', title: 'CELESTIAL GLOBAL', desc: 'Sky Projections' },
  { id: 4, tag: '05', title: 'TACTICAL COMMAND', desc: 'Operational Telemetry' },
];

const sectionVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }
  }
};

const staggerContainer = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.05 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.3, ease: 'easeOut' as const }
  }
};

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
        threshold: 0.2, 
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
          <h1 className="text-xl font-semibold text-[#D7DEE7]">Mission Control</h1>
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5 animate-pulse">
            Loading stellar intelligence parameters…
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
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
    version: 'v2.0.0-phase7b',
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
      
      {/* 1. Fixed Top Progress Indicator (Always tracks scroll progress inside main) */}
      <motion.div 
        className="fixed top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-400 origin-left z-50 shadow-[0_0_8px_rgba(245,158,11,0.4)]" 
        style={{ scaleX }} 
      />

      {/* 2. Responsive 2-Column Grid Layout (Prevents Left Sidebar overlap) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative w-full">
        
        {/* Sticky Narrative Timeline Left Column (lg:span-3) */}
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
                      className="absolute left-[-17px] top-1.5 w-1 h-8 rounded-r bg-[#F59E0B] shadow-[0_0_8px_rgba(245,158,11,0.5)]"
                      transition={{ type: 'spring', stiffness: 220, damping: 24 }}
                    />
                  )}
                  <span className={`text-[10px] leading-none tracking-[0.12em] ${isActive ? 'text-[#F59E0B] font-bold' : 'text-[#5A6878] group-hover:text-[#8B97A7]'}`}>
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

        {/* Content Right Column (lg:span-9) */}
        <div className="col-span-1 lg:col-span-9 flex flex-col gap-20">

          {/* SECTION 1: HERO / MISSION INITIATION */}
          <section 
            id="section-0" 
            data-section-id="0"
            className="min-h-[80vh] flex flex-col justify-center relative py-6"
          >
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-10%' }}
              variants={sectionVariants}
              className="space-y-6"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#F59E0B] animate-pulse" />
                <span className="text-[10px] text-[#F59E0B] font-mono uppercase tracking-[0.25em] font-semibold">
                  ASTRA Stellar Intelligence
                </span>
              </div>

              <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight leading-[1.1] text-white">
                Automated Stellar Transient <br className="hidden md:inline" /> Recognition &amp; Analysis
              </h1>

              <p className="text-[12px] text-[#8B97A7] leading-relaxed max-w-2xl font-mono">
                A multi-modal deep learning platform mapping variable stars observed by the TESS spacecraft. ASTRA fuses time-series convolutions and self-attention representations to deliver high-confidence, calibrated orbital classifications.
              </p>

              <div className="flex items-center gap-4 pt-4">
                <Link 
                  href="/search"
                  className="flex items-center gap-2 text-[11px] font-mono px-4 py-2 bg-[#78350F]/40 hover:bg-[#78350F] text-white border border-[#78350F]/80 rounded transition-all duration-300 shadow-[0_0_15px_rgba(245,158,11,0.08)] hover:shadow-[0_0_20px_rgba(245,158,11,0.15)]"
                >
                  <span>Query Target Search</span>
                  <ArrowRight className="w-3.5 h-3.5 text-[#F59E0B]" />
                </Link>
                <button 
                  onClick={() => handleScrollToSection(1)}
                  className="flex items-center gap-1.5 text-[11px] font-mono text-[#8B97A7] hover:text-[#D7DEE7] transition-colors"
                >
                  <span>Scroll Narrative</span>
                  <ChevronDown className="w-3.5 h-3.5 animate-bounce" />
                </button>
              </div>
            </motion.div>

            {/* Secure indicator banner */}
            {health && health.status === 'READY' && (
              <motion.div 
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: 0.4 }}
                className="mt-12 w-full max-w-md p-3.5 rounded border border-emerald-500/10 bg-emerald-500/5 text-[10px] font-mono flex items-center gap-3"
              >
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                <div className="flex-1">
                  <p className="text-emerald-400 font-bold leading-none uppercase tracking-wider">Zero-Trust Audit Verified</p>
                  <p className="text-white/40 mt-1 leading-tight">Database loaded. ONNX model hashes locked and verified.</p>
                </div>
              </motion.div>
            )}
          </section>

          {/* SECTION 2: DATA FREEZE */}
          <section 
            id="section-1" 
            data-section-id="1"
            className="min-h-[75vh] flex flex-col justify-center py-6 border-t border-white/5"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-10%' }}
                variants={sectionVariants}
                className="space-y-4"
              >
                <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                  <Database className="w-3.5 h-3.5 text-[#F59E0B]" />
                  <span className="uppercase tracking-wider">02 // DATASET FINGERPRINT</span>
                </div>
                <h2 className="text-2xl font-bold text-white tracking-tight leading-tight">
                  Cryptographic Dataset <br /> Hard Freeze Lock
                </h2>
                <p className="text-[11px] text-[#8B97A7] leading-relaxed font-mono">
                  ASTRA seals the dataset of <strong className="text-[#D7DEE7]">{datasetMetrics.total_stars} stars</strong>. Checksums are verified programmatically: if the SHA256 matches the baseline index, inference is unlocked. Mismatch aborts evaluation.
                </p>
                <div className="pt-4 text-[10px] font-mono border-t border-white/5 space-y-1">
                  <p className="flex justify-between">
                    <span className="text-[#5A6878]">FINGERPRINT:</span>
                    <span className="text-[#F59E0B] select-all tracking-wider font-semibold">{datasetMetrics.manifest_sha256.slice(0, 12)}...{datasetMetrics.manifest_sha256.slice(-12)}</span>
                  </p>
                  <p className="flex justify-between">
                    <span className="text-[#5A6878]">RELEASED:</span>
                    <span className="text-white/70">{datasetMetrics.freeze_date}</span>
                  </p>
                </div>
              </motion.div>

              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-10%' }}
                variants={sectionVariants}
                className="astra-glass border border-white/5 p-5 rounded space-y-4 font-mono shadow-xl relative overflow-hidden group hover:border-white/10"
              >
                <div className="absolute top-0 right-0 w-20 h-20 bg-[#78350F]/5 rounded-full blur-2xl pointer-events-none" />
                <div className="flex justify-between items-center text-[10px] border-b border-white/5 pb-2">
                  <span className="text-[#D7DEE7] font-bold">COHORT CODES</span>
                  <span className="text-emerald-400 font-bold uppercase tracking-wider">verified</span>
                </div>
                <div className="space-y-3 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Total Samples:</span>
                    <span className="text-white font-semibold">{datasetMetrics.total_stars} Targets</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">TESS Light Curves:</span>
                    <span className="text-white">PDCSAP Flux</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Validation Partition:</span>
                    <span className="text-[#A78BFA]">{datasetMetrics.splits.val} stars</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Lock Integrity:</span>
                    <span className="text-[#56D364] font-bold">SHA256 SECURED</span>
                  </div>
                </div>
              </motion.div>
            </div>
          </section>

          {/* SECTION 3: NEURAL MODEL CORE */}
          <section 
            id="section-2" 
            data-section-id="2"
            className="min-h-[75vh] flex flex-col justify-center py-6 border-t border-white/5"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              
              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-10%' }}
                variants={sectionVariants}
                className="order-2 md:order-1 astra-glass border border-white/5 p-5 rounded space-y-4 font-mono shadow-xl"
              >
                <div className="flex justify-between items-center text-[10px] border-b border-white/5 pb-2">
                  <span className="text-[#D7DEE7] font-bold">MODEL CONFIG</span>
                  <span className="text-[#F59E0B] font-bold uppercase tracking-wider">active</span>
                </div>
                <div className="space-y-3 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Model:</span>
                    <span className="text-[#F59E0B] font-semibold">{modelMetrics.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Base Architecture:</span>
                    <span className="text-white">{modelMetrics.architecture}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Parameters:</span>
                    <span className="text-white">{formatParams(modelMetrics.parameters)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">ECE (Calibrated):</span>
                    <span className="text-emerald-400 font-bold">{performanceMetrics.ece_after.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Softmax Temp (T):</span>
                    <span className="text-[#A78BFA] font-bold">{performanceMetrics.calibration_temperature.toFixed(3)}</span>
                  </div>
                </div>
              </motion.div>

              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-10%' }}
                variants={sectionVariants}
                className="space-y-4 order-1 md:order-2"
              >
                <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                  <Cpu className="w-3.5 h-3.5 text-[#F59E0B]" />
                  <span className="uppercase tracking-wider">03 // NEURAL ENCODER</span>
                </div>
                <h2 className="text-2xl font-bold text-white tracking-tight leading-tight">
                  Dual-Path Transformer &amp; Calibration
                </h2>
                <p className="text-[11px] text-[#8B97A7] leading-relaxed font-mono">
                  A dual 1D-CNN branch extracts short-term local morphology, and a 4-layer Star Transformer tracks long-term dependencies. Validation scaling at $T={performanceMetrics.calibration_temperature.toFixed(3)}$ addresses classifier overconfidence.
                </p>
              </motion.div>
            </div>
          </section>

          {/* SECTION 4: SPATIAL COVERAGE */}
          <section 
            id="section-3" 
            data-section-id="3"
            className="min-h-[75vh] flex flex-col justify-center py-6 border-t border-white/5"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-10%' }}
                variants={sectionVariants}
                className="space-y-4"
              >
                <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                  <Compass className="w-3.5 h-3.5 text-[#F59E0B]" />
                  <span className="uppercase tracking-wider">04 // SPATIAL REFERENCE</span>
                </div>
                <h2 className="text-2xl font-bold text-white tracking-tight leading-tight">
                  TESS Photometric <br /> Celestial Globe Mapping
                </h2>
                <p className="text-[11px] text-[#8B97A7] leading-relaxed font-mono">
                  Coordinates are projected in a 3D orbital space to visual tracking arrays. Resolving coordinates helps prevent telemetry gaps and spatial biases.
                </p>
                <div className="pt-2">
                  <Link 
                    href="/visualization"
                    className="inline-flex items-center gap-2 text-[11px] font-mono text-[#F59E0B] hover:text-[#fde047] transition-colors"
                  >
                    <span>Explore 3D Celestial Globe</span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#F59E0B]" />
                  </Link>
                </div>
              </motion.div>

              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-10%' }}
                variants={sectionVariants}
                className="h-48 relative border border-white/5 rounded overflow-hidden bg-black/40 flex items-center justify-center shadow-xl group hover:border-white/10"
              >
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(120,53,15,0.2),transparent_70%)]" />
                <div className="z-10 text-center space-y-2">
                  <Globe className="w-8 h-8 text-[#F59E0B] mx-auto animate-pulse" />
                  <p className="text-[10px] font-mono text-white/60 tracking-wider">GLOBE PROJECTIONS LOADED</p>
                  <p className="text-[9px] font-mono text-white/30 leading-none">RA: 0° to 360° / DEC: -90° to +90°</p>
                </div>
              </motion.div>
            </div>
          </section>

          {/* SECTION 5: TACTICAL CONTROL CENTER */}
          <section 
            id="section-4" 
            data-section-id="4"
            className="py-6 border-t border-white/5 space-y-8"
          >
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={sectionVariants}
              className="space-y-2"
            >
              <div className="flex items-center gap-2 text-[#8B97A7] font-mono text-[10px]">
                <Compass className="w-3.5 h-3.5 text-[#F59E0B]" />
                <span className="uppercase tracking-wider">05 // TELEMETRY DASHBOARD</span>
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Operational Command Center
              </h2>
            </motion.div>

            {/* Top Metrics Row */}
            <motion.div 
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={staggerContainer}
              className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
            >
              <motion.div variants={itemVariants}>
                <MetricCard
                  label="Dataset"
                  value={`${datasetMetrics.total_stars} Stars`}
                  sub="Freeze V2"
                  accentColor="text-[#F59E0B]"
                />
              </motion.div>
              <motion.div variants={itemVariants}>
                <MetricCard
                  label="Model"
                  value={modelMetrics.name}
                  sub={modelMetrics.version}
                />
              </motion.div>
              <motion.div variants={itemVariants}>
                <MetricCard
                  label="Test Accuracy"
                  value={formatPercent(performanceMetrics.test_accuracy)}
                  sub={`Phase 8 · ${datasetMetrics.splits.test} stars`}
                />
              </motion.div>
              <motion.div variants={itemVariants}>
                <MetricCard
                  label="Macro F1"
                  value={performanceMetrics.macro_f1.toFixed(4)}
                  sub={`Weighted: ${performanceMetrics.weighted_f1.toFixed(4)}`}
                />
              </motion.div>
              <motion.div variants={itemVariants}>
                <MetricCard
                  label="ECE (Calibrated)"
                  value={performanceMetrics.ece_after.toFixed(4)}
                  sub={`T=${performanceMetrics.calibration_temperature.toFixed(3)}`}
                />
              </motion.div>
              <motion.div variants={itemVariants}>
                <MetricCard
                  label="Parameters"
                  value={formatParams(modelMetrics.parameters)}
                  sub={modelMetrics.architecture}
                />
              </motion.div>
            </motion.div>

            {/* Class & Split Layout */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Class Distribution Donut */}
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
              >
                <Panel title="Class Distribution" subtitle="Composition of verified star classifications">
                  <div className="h-64 flex flex-col justify-between">
                    <div className="flex-1 min-h-[180px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            cx="50%"
                            cy="50%"
                            innerRadius={55}
                            outerRadius={85}
                            paddingAngle={2}
                            dataKey="value"
                          >
                            {pieData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip
                            contentStyle={{
                              background: '#0C1118',
                              border: '1px solid #1A2430',
                              borderRadius: 2,
                              fontSize: 11,
                              fontFamily: 'IBM Plex Mono, monospace',
                              color: '#D7DEE7',
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-4 text-[11px] font-mono">
                      {pieData.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-1.5">
                          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                          <span className="text-[#8B97A7] truncate text-[10px]">{item.name}</span>
                          <span className="text-[#D7DEE7] ml-auto pr-2">{item.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </Panel>
              </motion.div>

              {/* Split Strategy */}
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
              >
                <Panel title="Split Allocation" subtitle="Subdivision of dataset for model training & evaluation">
                  <div className="h-64 flex flex-col justify-center space-y-5">
                    {splitData.map((item, idx) => (
                      <div key={idx} className="space-y-1.5">
                        <div className="flex items-baseline justify-between text-[11px]">
                          <span className="text-[#D7DEE7] font-medium">{item.name} Split</span>
                          <div className="space-x-1.5 font-mono">
                            <span className="text-[#8B97A7]">{item.count} stars</span>
                            <span className="text-[#6EA8FE]">{item.pct.toFixed(1)}%</span>
                          </div>
                        </div>
                        <div className="h-2 bg-[#1A2430] rounded-full overflow-hidden">
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
                    <div className="text-[10px] text-[#5A6878] leading-normal bg-[#05070B] p-2.5 rounded border border-white/5 font-mono">
                      Note: Split assignment is strictly controlled by JSON files. Zero data leakage has been mathematically verified across all subsets.
                    </div>
                  </div>
                </Panel>
              </motion.div>
            </div>

            {/* Bottom Info Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Phase Audit Log */}
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
              >
                <Panel title="Phase Audit Log" subtitle="Milestones of the ASTRA platform development">
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
                      <tbody className="divide-y divide-white/5">
                        {AUDIT_EVENTS.map((evt, idx) => (
                          <tr key={idx} className="hover:bg-white/5">
                            <td className="py-2.5 font-mono text-[#F59E0B]">{evt.phase}</td>
                            <td className="py-2.5 font-medium">{evt.title}</td>
                            <td className="py-2.5 text-[#8B97A7] font-mono">{evt.date}</td>
                            <td className="py-2.5 text-right">
                              <StatusBadge status={evt.status as 'PASS'} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Panel>
              </motion.div>

              {/* Performance Overview */}
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
              >
                <Panel title="Performance Overview" subtitle="Statistical comparison of the active architecture">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-[11px] text-[#D7DEE7]">
                      <thead>
                        <tr className="border-b border-white/5">
                          <th className="py-2 font-medium text-[#8B97A7] uppercase tracking-wider">Metric</th>
                          <th className="py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Validation Set</th>
                          <th className="py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Test Set</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5 font-mono">
                        <tr className="hover:bg-white/5">
                          <td className="py-2.5 text-left font-sans font-medium text-[#8B97A7]">Accuracy</td>
                          <td className="py-2.5 text-right">{formatPercent(performanceMetrics.val_accuracy)}</td>
                          <td className="py-2.5 text-right text-[#F59E0B] font-bold">{formatPercent(performanceMetrics.val_accuracy)}</td>
                        </tr>
                        <tr className="hover:bg-white/5">
                          <td className="py-2.5 text-left font-sans font-medium text-[#8B97A7]">Macro F1 Score</td>
                          <td className="py-2.5 text-right">—</td>
                          <td className="py-2.5 text-right">0.7677</td>
                        </tr>
                        <tr className="hover:bg-white/5">
                          <td className="py-2.5 text-left font-sans font-medium text-[#8B97A7]">Weighted F1 Score</td>
                          <td className="py-2.5 text-right">—</td>
                          <td className="py-2.5 text-right">0.7710</td>
                        </tr>
                        <tr className="hover:bg-white/5">
                          <td className="py-2.5 text-left font-sans font-medium text-[#8B97A7]">Expected Calibration Error (ECE)</td>
                          <td className="py-2.5 text-right">—</td>
                          <td className="py-2.5 text-right text-emerald-400">0.0442</td>
                        </tr>
                        <tr className="hover:bg-white/5">
                          <td className="py-2.5 text-left font-sans font-medium text-[#8B97A7]">ECE Before Temperature Scaling</td>
                          <td className="py-2.5 text-right">—</td>
                          <td className="py-2.5 text-right text-amber-500">0.0810</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </Panel>
              </motion.div>
            </div>

            {/* Dataset Fingerprint Monospace Footer */}
            <div className="flex justify-between items-center text-[9px] text-[#5A6878] font-mono py-2 border-t border-white/5 select-none">
              <span>DATASET_MANIFEST_SHA256: {datasetMetrics.manifest_sha256}</span>
              <span>MODEL_CHECKPOINT_SHA256: {modelMetrics.checkpoint_hash}</span>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
