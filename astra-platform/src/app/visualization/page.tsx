'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useStars } from '@/lib/hooks';
import { useAstraStore } from '@/lib/store';
import { ClassBadge, PeriodSourceBadge, SplitBadge } from '@/components/shared/Badges';
import { Panel, EmptyState, MetricCard } from '@/components/shared/UI';
import { formatRA, formatDec, formatPeriod, CLASS_LABELS } from '@/lib/utils';
import Link from 'next/link';

// Dynamically import StarGlobe to avoid SSR issues with canvas/WebGL
const StarGlobe = dynamic(() => import('@/components/three/StarGlobe'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[350px] flex items-center justify-center font-mono text-[11px] text-[#5A6878]">
      Initializing WebGL context…
    </div>
  ),
});

export default function VisualizationPage() {
  const [selectedClass, setSelectedClass] = useState<string>('all');
  const { selectedStar, setSelectedStar } = useAstraStore();

  const { data, isLoading } = useStars({
    class: selectedClass !== 'all' ? selectedClass : undefined,
    limit: 944, // Fetch all stars matching class for full globe projection
  });

  return (
    <div className="space-y-6 h-[calc(100vh-7rem)] flex flex-col">
      {/* Page Header */}
      <div className="flex justify-between items-baseline shrink-0">
        <div>
          <h1 className="text-xl font-semibold text-[#D7DEE7]">3D Celestial Projections</h1>
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5">
            Spatial distribution map of verified variables on the celestial sphere
          </p>
        </div>
        <div className="font-mono text-[11px] text-[#5A6878]">
          Projection radius: R=25 kpc (scaled) · Stars shown:{' '}
          {data ? data.stars.length.toLocaleString() : 'Loading…'}
        </div>
      </div>

      {/* Class filters bar */}
      <div className="p-3 rounded astra-glass flex flex-wrap gap-2 items-center shrink-0">
        <span className="text-[10px] text-[#8B97A7] uppercase font-mono tracking-wider mr-2">
          Filter globe:
        </span>
        <button
          onClick={() => {
            setSelectedClass('all');
            setSelectedStar(null);
          }}
          className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
            selectedClass === 'all'
              ? 'bg-[#6EA8FE]/20 text-[#6EA8FE] border border-[#6EA8FE]/30'
              : 'bg-white/5 border border-white/5 text-[#8B97A7] hover:text-[#D7DEE7] hover:bg-white/10'
          }`}
        >
          All Targets
        </button>
        {Object.entries(CLASS_LABELS).map(([key, label]) => (
          <button
            key={key}
            onClick={() => {
              setSelectedClass(key);
              setSelectedStar(null);
            }}
            className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
              selectedClass === key
                ? 'bg-[#6EA8FE]/20 text-[#6EA8FE] border border-[#6EA8FE]/30'
                : 'bg-white/5 border border-white/5 text-[#8B97A7] hover:text-[#D7DEE7] hover:bg-white/10'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Main Workspace split */}
      <div className="flex-1 min-h-0 flex flex-col md:flex-row gap-6">
        {/* Three.js Globe rendering */}
        <div className="flex-1 astra-glass rounded overflow-hidden relative">
          {!isLoading && data ? (
            <StarGlobe stars={data.stars} />
          ) : (
            <div className="w-full h-full flex items-center justify-center font-mono text-[11px] text-[#5A6878]">
              Loading targets database…
            </div>
          )}
        </div>

        {/* Selected target info card */}
        <div className="w-full md:w-80 shrink-0 flex flex-col">
          {!selectedStar ? (
            <Panel title="Target Dossier" subtitle="Stellar classification metrics" className="flex-1 flex flex-col justify-center text-center">
              <EmptyState
                message="No target selected"
                sub="Click on any variable star node on the celestial globe to retrieve intelligence dossier."
              />
            </Panel>
          ) : (
            <Panel
              title={`TIC ${selectedStar.tic_id}`}
              subtitle="Stellar coordinates & classification"
              className="flex-1 flex flex-col justify-between overflow-y-auto"
            >
              <div className="space-y-4">
                <div className="flex flex-wrap gap-1.5">
                  <ClassBadge cls={selectedStar.astra_class} />
                  <PeriodSourceBadge source={selectedStar.period_source} />
                  <SplitBadge split={selectedStar.split} />
                </div>

                <div className="grid grid-cols-2 gap-3 text-[11px] border-t border-white/5 pt-3">
                  <div>
                    <span className="text-[#8B97A7] uppercase block text-[9px]">Right Ascension</span>
                    <span className="font-mono text-[#D7DEE7]">{formatRA(selectedStar.ra)}</span>
                  </div>
                  <div>
                    <span className="text-[#8B97A7] uppercase block text-[9px]">Declination</span>
                    <span className="font-mono text-[#D7DEE7]">{formatDec(selectedStar.dec)}</span>
                  </div>
                  <div>
                    <span className="text-[#8B97A7] uppercase block text-[9px]">Periodicity</span>
                    <span className="font-mono text-[#D7DEE7]">{formatPeriod(selectedStar.period)}</span>
                  </div>
                  <div>
                    <span className="text-[#8B97A7] uppercase block text-[9px]">TESS Sectors</span>
                    <span className="font-mono text-[#D7DEE7]">{selectedStar.n_sectors}</span>
                  </div>
                </div>

                <div className="border-t border-white/5 pt-3 text-[11px] space-y-1">
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Primary Source:</span>
                    <span className="text-[#D7DEE7] font-semibold">{selectedStar.primary_source ?? 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">Pipeline cadence:</span>
                    <span className="text-[#D7DEE7]">{selectedStar.cadence_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8B97A7]">SNR estimate:</span>
                    <span className="text-[#D7DEE7] font-mono">{selectedStar.snr_estimate?.toFixed(3) ?? 'N/A'}</span>
                  </div>
                </div>
              </div>

              <div className="border-t border-white/5 pt-4 mt-6 flex gap-2">
                <Link
                  href={`/target/${selectedStar.tic_id}`}
                  className="flex-1 text-center text-[11px] border border-[#1D3A6B] bg-[#1D3A6B]/20 hover:bg-[#1D3A6B]/40 text-[#6EA8FE] py-1.5 rounded transition-colors"
                >
                  Open Dossier
                </Link>
                <Link
                  href={`/analysis?tic_id=${selectedStar.tic_id}`}
                  className="flex-1 text-center text-[11px] border border-white/5 bg-white/5 text-[#D7DEE7] hover:bg-white/10 py-1.5 rounded transition-colors"
                >
                  Analyze curve
                </Link>
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
}
