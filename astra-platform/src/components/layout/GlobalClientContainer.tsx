'use client';

import React, { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { CommandPalette } from './CommandPalette';
import { CosmicBackground } from '../three/CosmicBackground';
import { useAstraStore } from '@/lib/store';
import { spaceHumSynth } from '@/lib/utils/SpaceHum';
import { motion, AnimatePresence } from 'framer-motion';

export function GlobalClientContainer({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { audioState } = useAstraStore();

  // Manage programmatic deep-space hum synthesis
  useEffect(() => {
    if (audioState === 'playing') {
      spaceHumSynth?.start();
    } else {
      spaceHumSynth?.stop();
    }
  }, [audioState]);

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
              initial={{ opacity: 0, scale: 0.995, y: 3 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.995, y: -3 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] as const }}
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
