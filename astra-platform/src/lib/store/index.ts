import { create } from 'zustand';
import type { Star, AstraClass, PeriodSource } from '../types';

interface SearchFilters {
  query: string;
  classes: AstraClass[];
  periodSources: PeriodSource[];
  split: 'all' | 'train' | 'val' | 'test';
}

interface AstraStore {
  selectedStar: Star | null;
  setSelectedStar: (star: Star | null) => void;

  filters: SearchFilters;
  setFilters: (filters: Partial<SearchFilters>) => void;
  resetFilters: () => void;

  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;

  replayStep: number;
  replayStarId: number | null;
  setReplayStep: (step: number) => void;
  setReplayStarId: (id: number | null) => void;

  audioState: 'muted' | 'playing';
  setAudioState: (state: 'muted' | 'playing') => void;
  audioVolume: number;
  setAudioVolume: (volume: number) => void;
  qualityState: 'low' | 'medium' | 'high';
  setQualityState: (state: 'low' | 'medium' | 'high') => void;
}

const defaultFilters: SearchFilters = {
  query: '',
  classes: [],
  periodSources: [],
  split: 'all',
};

export const useAstraStore = create<AstraStore>((set) => ({
  selectedStar: null,
  setSelectedStar: (star) => set({ selectedStar: star }),

  filters: defaultFilters,
  setFilters: (filters) =>
    set((state) => ({ filters: { ...state.filters, ...filters } })),
  resetFilters: () => set({ filters: defaultFilters }),

  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  replayStep: 0,
  replayStarId: null,
  setReplayStep: (step) => set({ replayStep: step }),
  setReplayStarId: (id) => set({ replayStarId: id }),

  audioState: 'muted',
  setAudioState: (audioState) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('astra-audio-state', audioState);
    }
    set({ audioState });
  },
  audioVolume: 0.5,
  setAudioVolume: (audioVolume) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('astra-audio-volume', String(audioVolume));
    }
    set({ audioVolume });
  },
  qualityState: 'high',
  setQualityState: (qualityState) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('astra-quality-state', qualityState);
    }
    set({ qualityState });
  },
}));
