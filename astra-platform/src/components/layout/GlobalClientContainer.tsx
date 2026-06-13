'use client';

import React, { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { CommandPalette } from './CommandPalette';
import { CosmicBackground } from '../three/CosmicBackground';
import { ParticleLayer } from '../shared/ParticleLayer';
import { useAstraStore } from '@/lib/store';
import { spaceHumSynth } from '@/lib/utils/SpaceHum';
import { motion, AnimatePresence } from 'framer-motion';

export function GlobalClientContainer({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { 
    audioState, 
    setAudioState, 
    audioVolume, 
    setAudioVolume, 
    qualityState, 
    setQualityState 
  } = useAstraStore();

  // Load from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedAudio = localStorage.getItem('astra-audio-state') as 'muted' | 'playing' | null;
      const savedVolume = localStorage.getItem('astra-audio-volume');
      const savedQuality = localStorage.getItem('astra-quality-state') as 'low' | 'medium' | 'high' | null;

      if (savedAudio) setAudioState(savedAudio);
      if (savedVolume) setAudioVolume(parseFloat(savedVolume));
      if (savedQuality) setQualityState(savedQuality);
    }
  }, [setAudioState, setAudioVolume, setQualityState]);

  // Manage programmatic deep-space hum synthesis
  useEffect(() => {
    if (audioState === 'playing') {
      spaceHumSynth?.start();
    } else {
      spaceHumSynth?.stop();
    }
  }, [audioState]);

  // Sync volume with synthesizer
  useEffect(() => {
    spaceHumSynth?.setVolume(audioVolume);
  }, [audioVolume]);

  // Clean up audio on unmount
  useEffect(() => {
    return () => {
      spaceHumSynth?.stop();
    };
  }, []);

  return (
    <div className="flex h-screen overflow-hidden text-[#D7DEE7]">
      {/* 3D Cosmic Starfield Layer (behind everything) */}
      <CosmicBackground />
      <ParticleLayer />

      {/* Global Navigation Sidebar */}
      <Sidebar />

      {/* Main Workspace Column */}
      <div className="flex flex-col flex-1 overflow-hidden relative z-10">
        {/* Telemetry and Global Action Top Bar */}
        <TopBar />

        {/* Dynamic Transition Area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 relative select-text">
          <AnimatePresence mode="wait">
            <motion.div
              key={pathname}
              initial={{ opacity: 0, y: 6, filter: 'blur(4px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -6, filter: 'blur(4px)' }}
              transition={{ duration: 0.35, ease: 'easeInOut' }}
              className="h-full w-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Global Shortcut Palette (Cmd+K / Ctrl+K) */}
      <CommandPalette />
    </div>
  );
}
