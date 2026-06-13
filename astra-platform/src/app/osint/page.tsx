'use client';

import { useState } from 'react';
import { useStars } from '@/lib/hooks';
import { ClassBadge, PeriodSourceBadge } from '@/components/shared/Badges';
import { Panel, EmptyState, DataRow } from '@/components/shared/UI';
import { formatRA, formatDec, formatPeriod, CLASS_LABELS } from '@/lib/utils';
import type { Star } from '@/lib/types';
import { useQuery } from '@tanstack/react-query';

interface OsintData {
  tic_id: number;
  astra_class: string;
  period: number;
  period_source: string;
  ra: number;
  dec: number;
  cross_matches: { catalog: string; identifier: string; otype: string; distance_arcsec: number; notes: string }[];
  observational_history: { observatory: string; instrument: string; filters: string; observations: number; first_obs: string; last_obs: string; cadence: string }[];
  related_objects: { identifier: string; class: string; ra: number; dec: number; separation: string; notes: string }[];
  provenance: { step: string; agent: string; detail: string }[];
  scientific_notes: string;
  audit_hash: string;
}

export default function SpaceOsintPage() {
  const [selectedStar, setSelectedStar] = useState<Star | null>(null);
  const [query, setQuery] = useState('');

  const { data: starsData, isLoading: starsLoading } = useStars({
    q: query || undefined,
    limit: 50,
  });

  const { data: osint, isLoading: osintLoading } = useQuery<OsintData>({
    queryKey: ['osint', selectedStar?.tic_id],
    queryFn: () => fetch(`/api/osint/${selectedStar?.tic_id}`).then((r) => r.json()),
    enabled: !!selectedStar,
  });

  const handleSelectStar = (star: Star) => {
    setSelectedStar(star);
  };

  return (
    <div className="flex gap-0 h-[calc(100vh-7rem)]">
      {/* Target Selector Sidebar */}
      <div className="w-64 shrink-0 rounded-l astra-glass border-r-0 flex flex-col">
        <div className="px-3 py-2.5 border-b border-white/5">
          <p className="text-[0.6875rem] uppercase tracking-widest text-[#8B97A7] mb-2 font-mono">
            OSINT Registry
          </p>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search Target ID…"
            className="w-full bg-[#05070B]/50 border border-white/5 rounded px-2.5 py-1.5 text-[0.75rem] text-[#D7DEE7] placeholder-[#5A6878] focus:outline-none focus:border-[#6EA8FE]"
          />
        </div>
        <div className="flex-1 overflow-y-auto">
          {starsLoading && (
            <p className="text-[0.75rem] text-[#5A6878] p-3 font-mono">Loading registry…</p>
          )}
          {starsData?.stars.map((star) => (
            <button
              key={star.tic_id}
              onClick={() => handleSelectStar(star)}
              className={`w-full text-left px-3 py-2 border-b border-white/5 hover:bg-white/5 transition-colors flex flex-col ${
                selectedStar?.tic_id === star.tic_id ? 'bg-[#1D3A6B]/30 border-l-2 border-l-[#6EA8FE]' : ''
              }`}
            >
              <span className="text-[11px] font-mono text-[#D7DEE7]">TIC {star.tic_id}</span>
              <div className="flex items-center gap-1.5 mt-1">
                <ClassBadge cls={star.astra_class} />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* OSINT Report workspace */}
      <div className="flex-1 rounded-r astra-glass flex flex-col overflow-hidden">
        {!selectedStar ? (
          <EmptyState
            message="Select a target star to generate Intelligence Report"
            sub="Cross-references TESS catalogs with SIMBAD, Gaia, and external variable registries."
          />
        ) : osintLoading ? (
          <div className="h-64 flex flex-col items-center justify-center space-y-2">
            <span className="text-[11px] text-[#5A6878] font-mono animate-pulse">Running cross-matching algorithms…</span>
          </div>
        ) : osint ? (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Header Banner */}
            <div className="pb-4 border-b border-[#1A2430] flex justify-between items-start">
              <div>
                <span className="text-[10px] text-emerald-400 font-mono tracking-widest uppercase block mb-1">
                  Target Intelligence Report · SECURE
                </span>
                <h1 className="text-xl font-bold text-[#D7DEE7] font-mono">TIC {selectedStar.tic_id}</h1>
                <p className="text-[11px] text-[#8B97A7] mt-1">
                  Source: TESS Input Catalog · Preprocessing: {selectedStar.preprocessing_version} · Hash: {osint.audit_hash.slice(0, 16)}…
                </p>
              </div>
              <div className="text-right space-y-1">
                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-mono">
                  VERIFIED LOCK
                </span>
                <p className="text-[9px] text-[#5A6878] font-mono">
                  AUDIT DATE: {new Date().toISOString().slice(0, 10)}
                </p>
              </div>
            </div>

            {/* Grid 1: Coordinates and Identity */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Coordinates */}
              <Panel title="Stellar Coordinates & Properties" subtitle="Spatial data and observations">
                <div className="space-y-0.5">
                  <DataRow label="Right Ascension (J2000)" value={formatRA(osint.ra)} mono />
                  <DataRow label="Declination (J2000)" value={formatDec(osint.dec)} mono />
                  <DataRow label="Periodicity (Selected)" value={formatPeriod(osint.period)} mono />
                  <DataRow label="Period Source Priority" value={osint.period_source} />
                  <DataRow label="TESS Sectors Count" value={selectedStar.n_sectors} mono />
                  <DataRow label="Signal to Noise Ratio (Est.)" value={selectedStar.snr_estimate?.toFixed(3) ?? 'N/A'} mono />
                </div>
              </Panel>

              {/* Scientific logs */}
              <Panel title="Scientific Notes" subtitle="Astronomical summary report">
                <div className="text-[11px] text-[#8B97A7] leading-relaxed font-sans astra-glass p-3.5 rounded">
                  {osint.scientific_notes}
                </div>
              </Panel>
            </div>

            {/* Cross Matches */}
            <Panel title="Astronomical Database Cross-Matches" subtitle="Cross-identification with celestial registries">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px] text-[#D7DEE7]">
                  <thead>
                    <tr className="border-b border-[#1A2430] bg-[#05070B]/50">
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Catalog</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider font-mono">Identifier</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Object Type</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Offset (arcsec)</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1A2430]">
                    {osint.cross_matches.map((item, idx) => (
                      <tr key={idx} className="hover:bg-[#111922]">
                        <td className="px-3 py-2 font-medium">{item.catalog}</td>
                        <td className="px-3 py-2 font-mono text-[#6EA8FE]">{item.identifier}</td>
                        <td className="px-3 py-2 text-[#8B97A7] font-mono">{item.otype}</td>
                        <td className="px-3 py-2 text-right font-mono">{item.distance_arcsec.toFixed(2)}</td>
                        <td className="px-3 py-2 text-[#8B97A7]">{item.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            {/* Observational History */}
            <Panel title="Astronomical Observations History" subtitle="Physical sensor logs">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px] text-[#D7DEE7]">
                  <thead>
                    <tr className="border-b border-[#1A2430] bg-[#05070B]/50">
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Observatory</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Instrument</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Filters</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Data Points</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider font-mono">Date Range</th>
                      <th className="px-3 py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Cadence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1A2430] font-mono">
                    {osint.observational_history.map((item, idx) => (
                      <tr key={idx} className="hover:bg-[#111922]">
                        <td className="px-3 py-2 font-sans font-medium text-[#D7DEE7]">{item.observatory}</td>
                        <td className="px-3 py-2 font-sans text-[#8B97A7]">{item.instrument}</td>
                        <td className="px-3 py-2 text-[#8B97A7]">{item.filters}</td>
                        <td className="px-3 py-2 text-right">{item.observations.toLocaleString()}</td>
                        <td className="px-3 py-2 text-[#8B97A7]">{item.first_obs} · {item.last_obs}</td>
                        <td className="px-3 py-2 font-sans text-[#8B97A7]">{item.cadence}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            {/* Grid 2: Related objects & Lineage */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Related objects */}
              <Panel title="Related Celestial Objects" subtitle="Nearby stellar coordinates in same sector">
                <div className="overflow-x-auto text-[11px]">
                  <table className="w-full text-left text-[#D7DEE7]">
                    <thead>
                      <tr className="border-b border-[#1A2430]">
                        <th className="py-1 font-medium text-[#8B97A7] uppercase font-mono">TIC ID</th>
                        <th className="py-1 font-medium text-[#8B97A7] uppercase text-right">Separation</th>
                        <th className="py-1 font-medium text-[#8B97A7] uppercase">Classification</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1A2430] font-mono">
                      {osint.related_objects.map((obj, idx) => (
                        <tr key={idx} className="hover:bg-[#111922]">
                          <td className="py-2 text-[#6EA8FE]">{obj.identifier}</td>
                          <td className="py-2 text-right">{obj.separation}</td>
                          <td className="py-2 font-sans text-[#8B97A7]">{obj.notes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>

              {/* Data Provenance */}
              <Panel title="Data Provenance & Lineage" subtitle="Chain of custody for raw sensors">
                <div className="space-y-3">
                  {osint.provenance.map((item, idx) => (
                    <div key={idx} className="flex gap-2.5 text-[11px] leading-tight items-start">
                      <span className="font-mono text-[#5A6878] w-4 mt-0.5">0{idx + 1}</span>
                      <div className="flex-1">
                        <span className="text-[#D7DEE7] font-semibold">{item.step}</span>
                        <span className="text-[#8B97A7] text-[10px] block mt-0.5">
                          Agent: {item.agent} · {item.detail}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>

            {/* Cryptographic Audit Trail */}
            <div className="p-3 bg-[#05070B] border border-[#1A2430] rounded flex items-center justify-between text-[10px] font-mono text-[#5A6878]">
              <span>AUDIT CHECKSUM: {osint.audit_hash}</span>
              <span className="text-emerald-400">ASTRA_OSINT_REPORT_PROVENANCE_PASS</span>
            </div>
          </div>
        ) : (
          <div className="p-6">
            <EmptyState message="OSINT Report could not be generated" sub="Please try selecting a different star target." />
          </div>
        )}
      </div>
    </div>
  );
}
