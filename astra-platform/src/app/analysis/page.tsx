'use client';

import { useState, useCallback } from 'react';
import { useStars, useLightCurve } from '@/lib/hooks';
import { ClassBadge, PeriodSourceBadge } from '@/components/shared/Badges';
import { Panel, EmptyState } from '@/components/shared/UI';
import { formatRA, formatDec, formatPeriod } from '@/lib/utils';
import type { Star } from '@/lib/types';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Brush,
} from 'recharts';

function sampleArray(arr: number[], maxPoints: number): { x: number; y: number }[] {
  if (!arr || arr.length === 0) return [];
  const step = Math.max(1, Math.floor(arr.length / maxPoints));
  const result = [];
  for (let i = 0; i < arr.length; i += step) {
    result.push({ x: i, y: +arr[i].toFixed(6) });
  }
  return result;
}

function LightCurveChart({
  ticId,
  title,
  type,
}: {
  ticId: number;
  title: string;
  type: 'raw' | 'folded';
}) {
  const { data, isLoading, isError } = useLightCurve(ticId);

  const chartData =
    type === 'raw'
      ? sampleArray(data?.flux_1000 ?? [], 500)
      : sampleArray(data?.folded_flux_200 ?? [], 200);

  return (
    <div className="astra-glass rounded">
      <div className="px-4 py-2.5 border-b border-white/5 flex items-center justify-between">
        <span className="text-[0.8125rem] font-medium text-[#D7DEE7]">{title}</span>
        {data && data.flux_1000 && data.folded_flux_200 && (
          <span className="text-[10px] font-mono text-[#5A6878]">
            {type === 'raw' ? `${data.flux_1000.length.toLocaleString()} pts` : `${data.folded_flux_200.length} pts`}
          </span>
        )}
      </div>
      <div className="p-4">
        {isLoading && (
          <div className="h-48 flex items-center justify-center">
            <span className="text-[0.75rem] text-[#5A6878]">Loading light curve…</span>
          </div>
        )}
        {isError && (
          <div className="h-48 flex items-center justify-center">
            <span className="text-[0.75rem] text-[#F85149]">Light curve unavailable</span>
          </div>
        )}
        {!isLoading && !isError && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={192}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="2 4" stroke="#1A2430" />
              <XAxis
                dataKey="x"
                tick={{ fill: '#5A6878', fontSize: 10 }}
                axisLine={{ stroke: '#1A2430' }}
                tickLine={false}
                label={{
                  value: type === 'raw' ? 'Index' : 'Phase Index',
                  position: 'insideBottom',
                  fill: '#5A6878',
                  fontSize: 10,
                  dy: 10,
                }}
              />
              <YAxis
                tick={{ fill: '#5A6878', fontSize: 10 }}
                axisLine={{ stroke: '#1A2430' }}
                tickLine={false}
                width={55}
                tickFormatter={(v) => v.toFixed(3)}
                label={{
                  value: 'Norm. Flux',
                  angle: -90,
                  position: 'insideLeft',
                  fill: '#5A6878',
                  fontSize: 10,
                  dx: -5,
                }}
              />
              <Tooltip
                contentStyle={{
                  background: '#0C1118',
                  border: '1px solid #1A2430',
                  borderRadius: 2,
                  fontSize: 11,
                  fontFamily: 'IBM Plex Mono, monospace',
                  color: '#D7DEE7',
                }}
                formatter={(v: any) => [typeof v === 'number' ? v.toFixed(5) : String(v), 'Flux']}
              />
              {type === 'raw' && (
                <Brush dataKey="x" height={16} stroke="#1A2430" fill="#0C1118" travellerWidth={4} />
              )}
              <Line
                type="monotone"
                dataKey="y"
                stroke="#6EA8FE"
                strokeWidth={1}
                dot={false}
                activeDot={{ r: 3, fill: '#6EA8FE' }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function StarListItem({
  star,
  isSelected,
  onClick,
}: {
  star: Star;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 border-b border-[#1A2430] hover:bg-[#111922] transition-colors ${
        isSelected ? 'bg-[#1D3A6B]/30 border-l-2 border-l-[#6EA8FE]' : ''
      }`}
    >
      <p className="text-[0.75rem] font-mono text-[#D7DEE7]">TIC {star.tic_id}</p>
      <div className="flex items-center gap-1.5 mt-0.5">
        <ClassBadge cls={star.astra_class} />
        <PeriodSourceBadge source={star.period_source} />
      </div>
    </button>
  );
}

export default function AnalysisPage() {
  const [selectedStar, setSelectedStar] = useState<Star | null>(null);
  const [query, setQuery] = useState('');
  const [activeChart, setActiveChart] = useState<'raw' | 'folded'>('raw');

  const { data, isLoading, isError, error } = useStars({
    q: query || undefined,
    limit: 100,
  });

  const handleSelect = useCallback((star: Star) => {
    setSelectedStar(star);
  }, []);

  return (
    <div className="flex gap-0 h-[calc(100vh-7rem)]">
      {/* Star Selector Sidebar */}
      <div className="w-56 shrink-0 rounded-l astra-glass border-r-0 flex flex-col">
        <div className="px-3 py-2.5 border-b border-white/5">
          <p className="text-[0.6875rem] uppercase tracking-widest text-[#8B97A7] mb-2">
            Select Target
          </p>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="TIC ID or class…"
            className="w-full bg-[#05070B]/50 border border-white/5 rounded px-2 py-1.5 text-[0.75rem] text-[#D7DEE7] placeholder-[#5A6878] focus:outline-none focus:border-[#6EA8FE]"
          />
        </div>
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <p className="text-[0.75rem] text-[#5A6878] p-3">Loading…</p>
          )}
          {isError && (
            <p className="text-[0.75rem] text-[#F85149] p-3 font-mono">
              Err: {error instanceof Error ? error.message : "Failed to load"}
            </p>
          )}
          {!isLoading && !isError && data?.stars && Array.isArray(data.stars) && data.stars.map((star) => (
            <StarListItem
              key={star.tic_id}
              star={star}
              isSelected={selectedStar?.tic_id === star.tic_id}
              onClick={() => handleSelect(star)}
            />
          ))}
        </div>
        <div className="px-3 py-2 border-t border-white/5">
          <p className="text-[10px] text-[#5A6878]">
            {typeof data?.total === 'number' ? data.total.toLocaleString() : 0} targets
          </p>
        </div>
      </div>

      {/* Analysis Panel */}
      <div className="flex-1 rounded-r astra-glass flex flex-col overflow-hidden">
        {!selectedStar ? (
          <EmptyState
            message="Select a target to begin analysis"
            sub="Choose any of the 944 stars from the panel on the left"
          />
        ) : (
          <>
            {/* Star Info Header */}
            <div className="px-4 py-3 border-b border-white/5 flex items-center gap-4 flex-wrap">
              <div>
                <p className="text-[0.6875rem] text-[#8B97A7] uppercase tracking-wider">Target</p>
                <p className="font-mono text-[0.875rem] text-[#D7DEE7]">TIC {selectedStar.tic_id}</p>
              </div>
              <ClassBadge cls={selectedStar.astra_class} />
              <PeriodSourceBadge source={selectedStar.period_source} />
              <div>
                <p className="text-[0.6875rem] text-[#8B97A7]">Period</p>
                <p className="font-mono text-[0.8125rem] text-[#D7DEE7]">
                  {formatPeriod(selectedStar.period)}
                </p>
              </div>
              <div>
                <p className="text-[0.6875rem] text-[#8B97A7]">RA / Dec</p>
                <p className="font-mono text-[0.8125rem] text-[#D7DEE7]">
                  {formatRA(selectedStar.ra)} / {formatDec(selectedStar.dec)}
                </p>
              </div>
              <div>
                <p className="text-[0.6875rem] text-[#8B97A7]">Sectors</p>
                <p className="font-mono text-[0.8125rem] text-[#D7DEE7]">{selectedStar.n_sectors}</p>
              </div>
              <div>
                <p className="text-[0.6875rem] text-[#8B97A7]">SNR</p>
                <p className="font-mono text-[0.8125rem] text-[#D7DEE7]">
                  {selectedStar.snr_estimate?.toFixed(3) ?? 'N/A'}
                </p>
              </div>
            </div>

            {/* Chart Toggle */}
            <div className="flex border-b border-white/5">
              {(['raw', 'folded'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setActiveChart(t)}
                  className={`px-4 py-2 text-[0.75rem] border-b-2 transition-colors ${
                    activeChart === t
                      ? 'border-[#6EA8FE] text-[#6EA8FE]'
                      : 'border-transparent text-[#8B97A7] hover:text-[#D7DEE7]'
                  }`}
                >
                  {t === 'raw' ? 'Normalized Flux (1000pt)' : 'Phase-Folded (200pt)'}
                </button>
              ))}
            </div>

            {/* Chart */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <LightCurveChart
                ticId={selectedStar.tic_id}
                title={
                  activeChart === 'raw'
                    ? `TIC ${selectedStar.tic_id} — Normalized Flux`
                    : `TIC ${selectedStar.tic_id} — Phase-Folded at P=${formatPeriod(selectedStar.period)}`
                }
                type={activeChart}
              />

              {/* Signal Statistics */}
              <Panel title="Signal Statistics" subtitle="Computed from raw metadata">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Raw Points', value: selectedStar.n_points_raw.toLocaleString() },
                    { label: 'Clean Points', value: selectedStar.n_points_clean.toLocaleString() },
                    {
                      label: 'Retention',
                      value: `${((selectedStar.n_points_clean / selectedStar.n_points_raw) * 100).toFixed(1)}%`,
                    },
                    { label: 'Variability Amp.', value: selectedStar.variability_amplitude?.toFixed(6) ?? 'N/A' },
                    { label: 'SNR Estimate', value: selectedStar.snr_estimate?.toFixed(3) ?? 'N/A' },
                    { label: 'BLS Power', value: selectedStar.bls_power?.toFixed(6) ?? 'N/A' },
                    { label: 'TESS Sectors', value: String(selectedStar.n_sectors) },
                    {
                      label: 'Cadence',
                      value: selectedStar.cadence_type ?? 'N/A',
                    },
                  ].map((item) => (
                    <div key={item.label}>
                      <p className="text-[0.6875rem] text-[#8B97A7] uppercase tracking-wider mb-0.5">
                        {item.label}
                      </p>
                      <p className="font-mono text-[0.875rem] text-[#D7DEE7]">{item.value}</p>
                    </div>
                  ))}
                </div>
              </Panel>

              {/* Period Comparison */}
              <Panel title="Period Comparison">
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-3 astra-glass rounded">
                    <p className="text-[0.6875rem] text-[#8B97A7] uppercase tracking-wider">Selected</p>
                    <p className="font-mono text-lg text-[#6EA8FE] mt-1">
                      {formatPeriod(selectedStar.period)}
                    </p>
                    <PeriodSourceBadge source={selectedStar.period_source} />
                  </div>
                  <div className="p-3 astra-glass rounded">
                    <p className="text-[0.6875rem] text-[#8B97A7] uppercase tracking-wider">Catalog</p>
                    <p className="font-mono text-lg text-[#D7DEE7] mt-1">
                      {selectedStar.catalog_period ? formatPeriod(selectedStar.catalog_period) : '—'}
                    </p>
                  </div>
                  <div className="p-3 astra-glass rounded">
                    <p className="text-[0.6875rem] text-[#8B97A7] uppercase tracking-wider">BLS</p>
                    <p className="font-mono text-lg text-[#D7DEE7] mt-1">
                      {selectedStar.bls_period ? formatPeriod(selectedStar.bls_period) : '—'}
                    </p>
                  </div>
                </div>
              </Panel>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
