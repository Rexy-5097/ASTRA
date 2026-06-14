import { useQuery } from '@tanstack/react-query';
import type { Star, StarsResponse, LightCurveData } from '../types';

// Robust fetch helper that checks r.ok and parses the JSON error details if present
async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) {
    const errorText = await r.text();
    let errorMessage = `HTTP error! status: ${r.status}`;
    try {
      const errJson = JSON.parse(errorText);
      errorMessage = errJson.error || errJson.details || errorMessage;
    } catch {
      // Not JSON
    }
    throw new Error(errorMessage);
  }
  return r.json();
}

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
    queryFn: () => fetchJson<StarsResponse>(`/api/stars?${searchParams}`),
  });
}

// ─── Single star ───────────────────────────────────────────────────────────────
export function useStar(id: string | number | null) {
  return useQuery<Star>({
    queryKey: ['star', id],
    queryFn: () => fetchJson<Star>(`/api/stars/${id}`),
    enabled: id !== null,
  });
}

// ─── Light curve ───────────────────────────────────────────────────────────────
export function useLightCurve(id: string | number | null) {
  return useQuery<LightCurveData>({
    queryKey: ['lightcurve', id],
    queryFn: () => fetchJson<LightCurveData>(`/api/lightcurve/${id}`),
    enabled: id !== null,
    staleTime: Infinity, // light curves don't change
  });
}

// ─── Search ────────────────────────────────────────────────────────────────────
export function useSearch(query: string) {
  return useQuery({
    queryKey: ['search', query],
    queryFn: () => fetchJson<any>(`/api/search?q=${encodeURIComponent(query)}`),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
}

// ─── Model details ─────────────────────────────────────────────────────────────
export function useModelDetails() {
  return useQuery({
    queryKey: ['model-details'],
    queryFn: () => fetchJson<any>('/api/model'),
  });
}

// ─── Checkpoints ───────────────────────────────────────────────────────────────
export function useCheckpoints() {
  return useQuery({
    queryKey: ['checkpoints'],
    queryFn: () => fetchJson<any>('/api/checkpoints'),
  });
}

// ─── Dataset metrics ───────────────────────────────────────────────────────────
export function useDatasetDetails() {
  return useQuery({
    queryKey: ['dataset-details'],
    queryFn: () => fetchJson<any>('/api/dataset'),
  });
}

// ─── Research findings ──────────────────────────────────────────────────────────
export function useResearchFindings() {
  return useQuery({
    queryKey: ['research-findings'],
    queryFn: () => fetchJson<any>('/api/research'),
  });
}

// ─── Benchmark metrics ─────────────────────────────────────────────────────────
export function useBenchmarkMetrics() {
  return useQuery({
    queryKey: ['benchmark-metrics'],
    queryFn: () => fetchJson<any>('/api/benchmark'),
  });
}

// ─── Calibration metrics ───────────────────────────────────────────────────────
export function useCalibrationDetails() {
  return useQuery({
    queryKey: ['calibration-details'],
    queryFn: () => fetchJson<any>('/api/calibration'),
  });
}

// ─── Explainability (ONNX) ─────────────────────────────────────────────────────
export function useExplain(id: string | number | null) {
  return useQuery({
    queryKey: ['explain', id],
    queryFn: () => fetchJson<any>(`/api/explain/${id}`),
    enabled: id !== null,
    staleTime: Infinity,
  });
}

// ─── Predict (PyTorch MC Dropout) ──────────────────────────────────────────────
export function usePredict(id: string | number | null) {
  return useQuery({
    queryKey: ['predict', id],
    queryFn: () => fetchJson<any>(`/api/predict/${id}`),
    enabled: id !== null,
    staleTime: Infinity,
  });
}
