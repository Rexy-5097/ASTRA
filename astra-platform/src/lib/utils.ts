import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { AstraClass, PeriodSource } from './types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRA(ra: number): string {
  const h = Math.floor(ra / 15);
  const m = Math.floor((ra / 15 - h) * 60);
  const s = ((ra / 15 - h) * 60 - m) * 60;
  return `${h.toString().padStart(2, '0')}h ${m.toString().padStart(2, '0')}m ${s.toFixed(2).padStart(5, '0')}s`;
}

export function formatDec(dec: number): string {
  const sign = dec >= 0 ? '+' : '-';
  const absDec = Math.abs(dec);
  const d = Math.floor(absDec);
  const m = Math.floor((absDec - d) * 60);
  const s = ((absDec - d) * 60 - m) * 60;
  return `${sign}${d.toString().padStart(2, '0')}° ${m.toString().padStart(2, '0')}' ${s.toFixed(1).padStart(4, '0')}"`;
}

export function formatPeriod(period: number): string {
  if (period >= 1) return `${period.toFixed(4)} d`;
  return `${(period * 24).toFixed(3)} h`;
}

export function formatNumber(n: number, decimals = 4): string {
  return n.toFixed(decimals);
}

export function formatPercent(n: number): string {
  return `${(n * 100).toFixed(2)}%`;
}

export function formatParams(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function formatHash(hash: string): string {
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`;
}

export const CLASS_LABELS: Record<AstraClass, string> = {
  rr_lyrae: 'RR Lyrae',
  cepheid: 'Cepheid',
  eclipsing_binary: 'Eclipsing Binary',
  solar_like: 'Solar-like',
  stable: 'Stable',
};

export const CLASS_COLORS: Record<AstraClass, string> = {
  rr_lyrae: '#F59E0B',
  cepheid: '#6EA8FE',
  eclipsing_binary: '#34D399',
  solar_like: '#A78BFA',
  stable: '#6B7280',
};

export const CLASS_BADGE_STYLE: Record<AstraClass, string> = {
  rr_lyrae: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
  cepheid: 'bg-blue-500/10 text-blue-400 border border-blue-500/30',
  eclipsing_binary: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
  solar_like: 'bg-purple-500/10 text-purple-400 border border-purple-500/30',
  stable: 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/30',
};

export const PERIOD_SOURCE_COLORS: Record<PeriodSource, string> = {
  catalog: '#56D364',
  BLS: '#D29922',
};

export function confidenceToColor(confidence: number): string {
  if (confidence >= 0.85) return '#56D364';
  if (confidence >= 0.70) return '#6EA8FE';
  if (confidence >= 0.55) return '#D29922';
  return '#F85149';
}

export function generateProbabilities(tic_id: number, true_class: AstraClass): Record<AstraClass, number> {
  const classes: AstraClass[] = ['rr_lyrae', 'cepheid', 'eclipsing_binary', 'solar_like', 'stable'];
  const seed = tic_id % 1000;
  const noise = (i: number) => (((seed * 31 + i * 17) % 100) / 100) * 0.15;
  
  const raw: Record<AstraClass, number> = {} as Record<AstraClass, number>;
  let sum = 0;
  for (let i = 0; i < classes.length; i++) {
    const cls = classes[i];
    const base = cls === true_class ? 0.7 + noise(i * 3) : 0.05 + noise(i);
    raw[cls] = Math.max(0.01, Math.min(0.99, base));
    sum += raw[cls];
  }
  
  const result: Record<AstraClass, number> = {} as Record<AstraClass, number>;
  for (const cls of classes) {
    result[cls] = raw[cls] / sum;
  }
  return result;
}
