import { useQuery } from '@tanstack/react-query';
import type { Star, StarsResponse, LightCurveData } from '../types';

// ─── Stars list ────────────────────────────────────────────────────────────────
interface StarsParams {
  q?: string;
  class?: string;
  source?: string;
  split?: string;
  page?: number;
  limit?: number;
}

export function useStars(params: StarsParams = {}) {
  const searchParams = new URLSearchParams();
  if (params.q) searchParams.set('q', params.q);
  if (params.class) searchParams.set('class', params.class);
  if (params.source) searchParams.set('source', params.source);
  if (params.split && params.split !== 'all') searchParams.set('split', params.split);
  if (params.page) searchParams.set('page', String(params.page));
  if (params.limit) searchParams.set('limit', String(params.limit));

  return useQuery<StarsResponse>({
    queryKey: ['stars', params],
    queryFn: () =>
      fetch(`/api/stars?${searchParams}`).then((r) => r.json()),
  });
}

// ─── Single star ───────────────────────────────────────────────────────────────
export function useStar(id: string | number | null) {
  return useQuery<Star>({
    queryKey: ['star', id],
    queryFn: () => fetch(`/api/stars/${id}`).then((r) => r.json()),
    enabled: id !== null,
  });
}

// ─── Light curve ───────────────────────────────────────────────────────────────
export function useLightCurve(id: string | number | null) {
  return useQuery<LightCurveData>({
    queryKey: ['lightcurve', id],
    queryFn: () => fetch(`/api/lightcurve/${id}`).then((r) => r.json()),
    enabled: id !== null,
    staleTime: Infinity, // light curves don't change
  });
}

// ─── Search ────────────────────────────────────────────────────────────────────
export function useSearch(query: string) {
  return useQuery({
    queryKey: ['search', query],
    queryFn: () =>
      fetch(`/api/search?q=${encodeURIComponent(query)}`).then((r) => r.json()),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}

// ─── Model details ─────────────────────────────────────────────────────────────
export function useModelDetails() {
  return useQuery({
    queryKey: ['model-details'],
    queryFn: () => fetch('/api/model').then((r) => r.json()),
  });
}

// ─── Checkpoints ───────────────────────────────────────────────────────────────
export function useCheckpoints() {
  return useQuery({
    queryKey: ['checkpoints'],
    queryFn: () => fetch('/api/checkpoints').then((r) => r.json()),
  });
}

// ─── Dataset metrics ───────────────────────────────────────────────────────────
export function useDatasetDetails() {
  return useQuery({
    queryKey: ['dataset-details'],
    queryFn: () => fetch('/api/dataset').then((r) => r.json()),
  });
}

// ─── Research findings ──────────────────────────────────────────────────────────
export function useResearchFindings() {
  return useQuery({
    queryKey: ['research-findings'],
    queryFn: () => fetch('/api/research').then((r) => r.json()),
  });
}

// ─── Benchmark metrics ─────────────────────────────────────────────────────────
export function useBenchmarkMetrics() {
  return useQuery({
    queryKey: ['benchmark-metrics'],
    queryFn: () => fetch('/api/benchmark').then((r) => r.json()),
  });
}

// ─── Calibration metrics ───────────────────────────────────────────────────────
export function useCalibrationDetails() {
  return useQuery({
    queryKey: ['calibration-details'],
    queryFn: () => fetch('/api/calibration').then((r) => r.json()),
  });
}

// ─── Explainability (ONNX) ─────────────────────────────────────────────────────
export function useExplain(id: string | number | null) {
  return useQuery({
    queryKey: ['explain', id],
    queryFn: () => fetch(`/api/explain/${id}`).then((r) => r.json()),
    enabled: id !== null,
    staleTime: Infinity,
  });
}

// ─── Predict (PyTorch MC Dropout) ──────────────────────────────────────────────
export function usePredict(id: string | number | null) {
  return useQuery({
    queryKey: ['predict', id],
    queryFn: () => fetch(`/api/predict/${id}`).then((r) => r.json()),
    enabled: id !== null,
    staleTime: Infinity,
  });
}
