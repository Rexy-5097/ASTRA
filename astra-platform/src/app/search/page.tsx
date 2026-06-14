'use client';

import { useState, useEffect } from 'react';
import { useStars } from '@/lib/hooks';
import { ClassBadge, PeriodSourceBadge, SplitBadge } from '@/components/shared/Badges';
import { EmptyState, LoadingRows } from '@/components/shared/UI';
import { formatRA, formatDec, formatPeriod, CLASS_LABELS } from '@/lib/utils';
import type { AstraClass, PeriodSource } from '@/lib/types';
import Link from 'next/link';

export default function TargetSearchPage() {
  const [inputValue, setInputValue] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [selectedClass, setSelectedClass] = useState<string>('all');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [selectedSplit, setSelectedSplit] = useState<string>('all');
  const [page, setPage] = useState(1);
  const limit = 20;

  // Debounce the text query input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(inputValue);
      setPage(1); // Reset page on query change
    }, 300);
    return () => clearTimeout(handler);
  }, [inputValue]);

  // Hook fetching data
  const { data, isLoading, isError, error } = useStars({
    q: debouncedQuery || undefined,
    class: selectedClass !== 'all' ? selectedClass : undefined,
    source: selectedSource !== 'all' ? selectedSource : undefined,
    split: selectedSplit !== 'all' ? selectedSplit : undefined,
    page,
    limit,
  });

  const handleClassToggle = (cls: string) => {
    setSelectedClass(cls);
    setPage(1);
  };

  const handleSourceToggle = (src: string) => {
    setSelectedSource(src);
    setPage(1);
  };

  const handleSplitToggle = (split: string) => {
    setSelectedSplit(split);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-baseline">
        <div>
          <h1 className="text-xl font-semibold text-[#D7DEE7]">Target Search</h1>
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5">
            Query and filter ASTRA target registry
          </p>
        </div>
        <div className="font-mono text-[11px] text-[#5A6878]">
          {data && typeof data.total === 'number' ? `${data.total.toLocaleString()} targets match filter` : 'Loading registry…'}
        </div>
      </div>

      {/* Filter panel */}
      <div className="p-4 rounded astra-glass space-y-4">
        {/* Text Search Input */}
        <div>
          <label className="block text-[10px] text-[#8B97A7] uppercase tracking-wider mb-1.5">Search Query</label>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Search by TIC ID, primary catalog, label…"
            className="w-full bg-[#05070B] border border-[#1A2430] rounded px-3 py-2 text-[0.8125rem] text-[#D7DEE7] placeholder-[#5A6878] focus:outline-none focus:border-[#6EA8FE]"
          />
        </div>

        {/* Classes toggle */}
        <div>
          <label className="block text-[10px] text-[#8B97A7] uppercase tracking-wider mb-1.5">Class Selection</label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => handleClassToggle('all')}
              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                selectedClass === 'all'
                  ? 'bg-[#6EA8FE]/20 text-[#6EA8FE] border border-[#6EA8FE]/30'
                  : 'bg-[#05070B] border border-[#1A2430] text-[#8B97A7] hover:text-[#D7DEE7] hover:bg-[#111922]'
              }`}
            >
              All Classes
            </button>
            {Object.entries(CLASS_LABELS).map(([key, label]) => (
              <button
                key={key}
                onClick={() => handleClassToggle(key)}
                className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                  selectedClass === key
                    ? 'bg-[#6EA8FE]/20 text-[#6EA8FE] border border-[#6EA8FE]/30'
                    : 'bg-[#05070B] border border-[#1A2430] text-[#8B97A7] hover:text-[#D7DEE7] hover:bg-[#111922]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Triple Toggle row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Period source filter */}
          <div>
            <label className="block text-[10px] text-[#8B97A7] uppercase tracking-wider mb-1.5">Period Source</label>
            <div className="flex gap-2">
              {['all', 'catalog', 'BLS'].map((src) => (
                <button
                  key={src}
                  onClick={() => handleSourceToggle(src)}
                  className={`flex-1 px-2.5 py-1 text-[11px] font-medium rounded transition-colors text-center border ${
                    selectedSource === src
                      ? 'bg-[#6EA8FE]/20 text-[#6EA8FE] border-[#6EA8FE]/30'
                      : 'bg-[#05070B] border-[#1A2430] text-[#8B97A7] hover:text-[#D7DEE7] hover:bg-[#111922]'
                  }`}
                >
                  {src === 'all' ? 'All Sources' : src === 'catalog' ? 'Catalog' : 'BLS'}
                </button>
              ))}
            </div>
          </div>

          {/* Split filter */}
          <div>
            <label className="block text-[10px] text-[#8B97A7] uppercase tracking-wider mb-1.5">Dataset Split</label>
            <div className="flex gap-2">
              {['all', 'train', 'val', 'test'].map((split) => (
                <button
                  key={split}
                  onClick={() => handleSplitToggle(split)}
                  className={`flex-1 px-2.5 py-1 text-[11px] font-medium rounded transition-colors text-center border ${
                    selectedSplit === split
                      ? 'bg-[#6EA8FE]/20 text-[#6EA8FE] border-[#6EA8FE]/30'
                      : 'bg-[#05070B] border-[#1A2430] text-[#8B97A7] hover:text-[#D7DEE7] hover:bg-[#111922]'
                  }`}
                >
                  {split === 'all' ? 'All Splits' : split.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Results Panel */}
      <div className="astra-glass rounded overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px] text-[#D7DEE7]">
            <thead>
              <tr className="bg-[#05070B]/50 border-b border-white/5">
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider w-24">TIC ID</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider w-36">Class</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider w-28">Source</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider w-24">Period</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider">RA</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider">Dec</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider w-16 text-center">Sectors</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider w-16">Split</th>
                <th className="px-4 py-2.5 font-medium text-[#8B97A7] uppercase tracking-wider w-16 text-right">Dossier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1A2430]">
              {isLoading && <LoadingRows count={10} />}
              {!isLoading && isError && (
                <tr>
                  <td colSpan={9} className="py-8">
                    <EmptyState
                      message="Failed to load target registry"
                      sub={error instanceof Error ? error.message : "An unknown error occurred."}
                    />
                  </td>
                </tr>
              )}
              {!isLoading && !isError && (!data || !data.stars || data.stars.length === 0) && (
                <tr>
                  <td colSpan={9} className="py-8">
                    <EmptyState
                      message="No target stars match filter parameters"
                      sub="Try broadening search terms or removing filtering options"
                    />
                  </td>
                </tr>
              )}
              {!isLoading && !isError &&
                data?.stars && Array.isArray(data.stars) &&
                data.stars.map((star) => (
                  <tr key={star.tic_id} className="hover:bg-[#111922]">
                    <td className="px-4 py-2.5 font-mono">
                      <Link
                        href={`/target/${star.tic_id}`}
                        className="text-[#6EA8FE] hover:underline"
                      >
                        TIC {star.tic_id}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5">
                      <ClassBadge cls={star.astra_class} />
                    </td>
                    <td className="px-4 py-2.5">
                      <PeriodSourceBadge source={star.period_source} />
                    </td>
                    <td className="px-4 py-2.5 font-mono">
                      {formatPeriod(star.period)}
                    </td>
                    <td className="px-4 py-2.5 font-mono">{formatRA(star.ra)}</td>
                    <td className="px-4 py-2.5 font-mono">{formatDec(star.dec)}</td>
                    <td className="px-4 py-2.5 text-center font-mono">{star.n_sectors}</td>
                    <td className="px-4 py-2.5">
                      <SplitBadge split={star.split} />
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      <Link
                        href={`/target/${star.tic_id}`}
                        className="text-[10px] border border-[#1D3A6B] bg-[#1D3A6B]/20 hover:bg-[#1D3A6B]/40 text-[#6EA8FE] px-2 py-0.5 rounded transition-colors"
                      >
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* Pagination bar */}
        {data && data.pages > 1 && (
          <div className="px-4 py-3 border-t border-[#1A2430] flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 bg-[#05070B] border border-[#1A2430] text-[#8B97A7] hover:text-[#D7DEE7] disabled:opacity-50 disabled:hover:text-[#8B97A7] rounded text-[11px] transition-colors"
            >
              Previous
            </button>
            <div className="font-mono text-[11px] text-[#8B97A7]">
              Page <span className="text-[#D7DEE7]">{page}</span> of{' '}
              <span className="text-[#D7DEE7]">{data.pages}</span>
            </div>
            <button
              onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
              disabled={page === data.pages}
              className="px-3 py-1 bg-[#05070B] border border-[#1A2430] text-[#8B97A7] hover:text-[#D7DEE7] disabled:opacity-50 disabled:hover:text-[#8B97A7] rounded text-[11px] transition-colors"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
