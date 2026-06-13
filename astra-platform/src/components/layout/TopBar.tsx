'use client';

import { usePathname } from 'next/navigation';
import { Clock, Volume2, VolumeX, ShieldCheck, Cpu, ToggleLeft, ToggleRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useAstraStore } from '@/lib/store';

const PAGE_TITLES: Record<string, string> = {
  '/': 'Mission Control',
  '/search': 'Target Search',
  '/analysis': 'Light Curve Analysis',
  '/dataset': 'Dataset Intelligence',
  '/model': 'Model Operations',
  '/research': 'Research Findings',
  '/mission-replay': 'Mission Replay',
  '/osint': 'Space OSINT',
  '/visualization': '3D Visualization',
};

interface HealthInfo {
  status: 'READY' | 'DEGRADED' | 'BLOCKED' | 'LOADING';
  dataset_verified: boolean;
  model_verified: boolean;
  onnx_loaded: boolean;
  sqlite_loaded: boolean;
}

export function TopBar() {
  const pathname = usePathname();
  const [time, setTime] = useState('');
  const [health, setHealth] = useState<HealthInfo>({
    status: 'LOADING',
    dataset_verified: false,
    model_verified: false,
    onnx_loaded: false,
    sqlite_loaded: false,
  });

  const { 
    audioState, 
    setAudioState, 
    audioVolume, 
    setAudioVolume, 
    qualityState, 
    setQualityState 
  } = useAstraStore();

  useEffect(() => {
    const update = () => setTime(new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC');
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const fetchHealth = () => {
      fetch('/api/health')
        .then((res) => res.json())
        .then((data) => {
          setHealth({
            status: data.status || 'BLOCKED',
            dataset_verified: data.details?.dataset_hash_match ?? false,
            model_verified: (data.details?.onnx_exists ?? false) && (data.details?.dataset_hash_match ?? false),
            onnx_loaded: data.onnx_loaded ?? false,
            sqlite_loaded: data.sqlite_loaded ?? false,
          });
        })
        .catch(() => {
          setHealth({
            status: 'BLOCKED',
            dataset_verified: false,
            model_verified: false,
            onnx_loaded: false,
            sqlite_loaded: false,
          });
        });
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 15000); // refresh every 15s
    return () => clearInterval(interval);
  }, []);

  const title =
    PAGE_TITLES[pathname] ??
    (pathname.startsWith('/target/') ? 'Target Dossier' : 'ASTRA');

  const getStatusDotColor = (statusVal: string | boolean) => {
    if (statusVal === 'READY' || statusVal === true || statusVal === 'READY') return '#56D364';
    if (statusVal === 'DEGRADED') return '#D29922';
    if (statusVal === 'LOADING') return '#8B97A7';
    return '#F85149';
  };

  const getStatusLabel = (statusVal: string) => {
    switch (statusVal) {
      case 'READY': return 'VERIFIED';
      case 'DEGRADED': return 'DEGRADED';
      case 'BLOCKED': return 'ABORTED';
      default: return 'CHECKING';
    }
  };

  return (
    <header
      className="flex items-center justify-between h-12 px-4 border-b shrink-0 astra-glass"
      style={{ borderColor: '#1A2430' }}
    >
      {/* Left section: Page title & platform verify badge */}
      <div className="flex items-center gap-3">
        <span
          className="text-[0.8125rem] font-semibold tracking-wide"
          style={{ color: '#D7DEE7' }}
        >
          {title}
        </span>
        <span
          className="text-[9px] px-1.5 py-0.5 rounded border font-mono uppercase tracking-widest"
          style={{ color: '#6EA8FE', borderColor: '#1D3A6B', background: '#1D3A6B30' }}
        >
          Phase 8 Locked
        </span>
      </div>

      {/* Right section: Live Status Bar, Settings, and Clock */}
      <div className="flex items-center gap-6">
        
        {/* Telemetry Status Bar */}
        <div className="hidden lg:flex items-center gap-4 border-r border-[#1A2430] pr-6 h-6 text-[10px] font-mono select-none">
          <div className="flex items-center gap-1.5">
            <span className="text-[#5A6878]">DATASET</span>
            <span style={{ color: getStatusDotColor(health.dataset_verified) }}>●</span>
            <span style={{ color: health.dataset_verified ? '#D7DEE7' : '#8B97A7' }}>
              {health.dataset_verified ? 'VERIFIED' : 'UNVERIFIED'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[#5A6878]">MODEL</span>
            <span style={{ color: getStatusDotColor(health.model_verified) }}>●</span>
            <span style={{ color: health.model_verified ? '#D7DEE7' : '#8B97A7' }}>
              {health.model_verified ? 'VERIFIED' : 'DEGRADED'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[#5A6878]">ONNX</span>
            <span style={{ color: getStatusDotColor(health.onnx_loaded) }}>●</span>
            <span style={{ color: health.onnx_loaded ? '#D7DEE7' : '#8B97A7' }}>
              {health.onnx_loaded ? 'VERIFIED' : 'FAILED'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-[#5A6878]">SQLITE</span>
            <span style={{ color: getStatusDotColor(health.sqlite_loaded) }}>●</span>
            <span style={{ color: health.sqlite_loaded ? '#D7DEE7' : '#8B97A7' }}>
              {health.sqlite_loaded ? 'VERIFIED' : 'FAILED'}
            </span>
          </div>

          <div className="flex items-center gap-1.5 border-l border-[#1A2430] pl-4">
            <span className="text-[#5A6878]">SYSTEM</span>
            <span style={{ color: getStatusDotColor(health.status) }}>●</span>
            <span style={{ color: getStatusDotColor(health.status) }} className="font-semibold">
              {health.status}
            </span>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex items-center gap-3 border-r border-[#1A2430] pr-6 h-6 select-none">
          {/* Quality control */}
          <button
            onClick={() => {
              if (qualityState === 'low') setQualityState('medium');
              else if (qualityState === 'medium') setQualityState('high');
              else setQualityState('low');
            }}
            className="flex items-center gap-1 text-[10px] font-mono text-[#8B97A7] hover:text-[#D7DEE7] transition-colors"
            title="Toggle graphics quality (low: static, medium: video, high: particle effects)"
          >
            <Cpu className="w-3.5 h-3.5" />
            <span className="text-[9px]">GFX:</span>
            <span className="text-[#6EA8FE] font-bold">
              {qualityState.toUpperCase()}
            </span>
          </button>

          {/* Sound control */}
          <div className="flex items-center gap-2 pl-2 border-l border-[#1A2430]">
            <button
              onClick={() => setAudioState(audioState === 'muted' ? 'playing' : 'muted')}
              className="flex items-center gap-1 text-[10px] font-mono text-[#8B97A7] hover:text-[#D7DEE7] transition-colors"
              title="Toggle elegant space ambient audio"
            >
              {audioState === 'playing' ? (
                <Volume2 className="w-3.5 h-3.5 text-[#56D364] animate-pulse" />
              ) : (
                <VolumeX className="w-3.5 h-3.5 text-[#F85149]" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={audioVolume}
              onChange={(e) => {
                const vol = parseFloat(e.target.value);
                setAudioVolume(vol);
                if (vol > 0 && audioState === 'muted') {
                  setAudioState('playing');
                } else if (vol === 0 && audioState === 'playing') {
                  setAudioState('muted');
                }
              }}
              className="w-12 h-1 bg-[#1A2430] rounded-lg appearance-none cursor-pointer accent-[#6EA8FE]"
              style={{
                background: `linear-gradient(to right, #6EA8FE 0%, #6EA8FE ${audioVolume * 100}%, #1A2430 ${audioVolume * 100}%, #1A2430 100%)`
              }}
              title="Ambient audio volume"
            />
          </div>
        </div>

        {/* Clock telemetry */}
        <div className="flex items-center gap-1.5 text-[#8B97A7]">
          <Clock className="w-3.5 h-3.5 shrink-0" />
          <span className="text-[11px] font-mono tracking-wide">{time}</span>
        </div>
      </div>
    </header>
  );
}
