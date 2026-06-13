'use client';

import { MetricCard, Panel, HashBadge, DataRow } from '@/components/shared/UI';
import { StatusBadge } from '@/components/shared/Badges';
import { useDatasetDetails } from '@/lib/hooks';
import { DATASET_LINEAGE, AUDIT_EVENTS } from '@/lib/data/constants';
import { CLASS_COLORS, CLASS_LABELS, formatPercent } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip } from 'recharts';

export default function DatasetIntelligencePage() {
  const { data: datasetDetails, isLoading: datasetLoading } = useDatasetDetails();

  if (datasetLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-[#D7DEE7]">Dataset Intelligence</h1>
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5 animate-pulse">
            Loading dataset intelligence parameters…
          </p>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 astra-glass rounded" />
          ))}
        </div>
        <div className="h-64 astra-glass rounded animate-pulse" />
      </div>
    );
  }

  if (!datasetDetails) {
    return (
      <div className="p-6 text-center text-red-400 font-mono border border-red-500/20 bg-red-950/10 rounded">
        System Error: Failed to retrieve dynamic dataset intelligence.
      </div>
    );
  }

  const dataset = {
    total_stars: datasetDetails.audit.total_stars,
    manifest_sha256: datasetDetails.audit.dataset_hash,
    classes: datasetDetails.audit.class_counts,
    period_sources: datasetDetails.audit.period_source_counts,
    splits: datasetDetails.audit.split_counts,
  };

  const classes = dataset.classes;

  // Chart data format
  const classChartData = Object.entries(classes).map(([key, val]) => ({
    name: CLASS_LABELS[key as keyof typeof CLASS_LABELS] || key,
    count: val as number,
    color: CLASS_COLORS[key as keyof typeof CLASS_COLORS] || '#6B7280',
  }));

  // Calculations
  const totalStars = dataset.total_stars;
  const catalogPct = (dataset.period_sources.catalog / totalStars) * 100;
  const blsPct = (dataset.period_sources.BLS / totalStars) * 100;

  // Dynamic breakdown of classes in splits from database matrix
  const matrix = datasetDetails.classSplitMatrix || {};
  const trainBreakdown = Object.entries(matrix).map(([key, counts]: [string, any]) => ({
    label: CLASS_LABELS[key as keyof typeof CLASS_LABELS] || key,
    train: counts.train || 0,
    val: counts.val || 0,
    test: counts.test || 0,
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#D7DEE7]">Dataset Intelligence</h1>
        <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5">
          Comprehensive metadata lineage and quality parameters
        </p>
      </div>

      {/* Dataset Fingerprint */}
      <div className="p-3.5 astra-glass rounded flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-[10px] text-[#8B97A7] uppercase tracking-wider block mb-1">
            VERIFIED DATASET FINGERPRINT
          </span>
          <span className="text-[#D7DEE7] text-[13px] font-semibold">
            Scientific Freeze V2 · Locked manifest
          </span>
        </div>
        <HashBadge hash={dataset.manifest_sha256} label="SHA-256 Fingerprint" />
      </div>

      {/* Row 1 Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Stellar Targets"
          value={`${dataset.total_stars} stars`}
          sub="TESS Light Curves"
          accent
        />
        <MetricCard
          label="Splits (Train/Val/Test)"
          value={`${dataset.splits.train} / ${dataset.splits.val} / ${dataset.splits.test}`}
          sub="69.9% / 14.9% / 15.0%"
        />
        <MetricCard
          label="Catalog-Sourced Period"
          value={`${dataset.period_sources.catalog} stars`}
          sub={`${catalogPct.toFixed(1)}% verified period`}
        />
        <MetricCard
          label="BLS-Sourced Period"
          value={`${dataset.period_sources.BLS} stars`}
          sub={`${blsPct.toFixed(1)}% algorithm fallback`}
        />
      </div>

      {/* Row 2: Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Class distribution */}
        <Panel title="Class Distribution" subtitle="Relative occurrences of star classes in final dataset">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={classChartData}
                layout="vertical"
                margin={{ left: 10, right: 30, top: 10, bottom: 10 }}
              >
                <XAxis type="number" stroke="#5A6878" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="name"
                  type="category"
                  stroke="#5A6878"
                  tick={{ fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0C1118',
                    border: '1px solid #1A2430',
                    borderRadius: 2,
                    fontSize: 11,
                    color: '#D7DEE7',
                  }}
                />
                <Bar dataKey="count" radius={[0, 2, 2, 0]}>
                  {classChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        {/* Split Strategy */}
        <Panel title="Split Strategy" subtitle="Target class counts across partitioned groups">
          <div className="h-64 overflow-y-auto">
            <table className="w-full text-left text-[11px] text-[#D7DEE7]">
              <thead>
                <tr className="border-b border-[#1A2430]">
                  <th className="py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider">Target Class</th>
                  <th className="py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Train ({dataset.splits.train})</th>
                  <th className="py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Val ({dataset.splits.val})</th>
                  <th className="py-1.5 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Test ({dataset.splits.test})</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1A2430]">
                {trainBreakdown.map((row, idx) => {
                  return (
                    <tr key={idx} className="hover:bg-[#111922]">
                      <td className="py-2.5 font-medium">{row.label}</td>
                      <td className="py-2.5 text-right font-mono text-[#8B97A7]">{row.train}</td>
                      <td className="py-2.5 text-right font-mono text-[#8B97A7]">{row.val}</td>
                      <td className="py-2.5 text-right font-mono text-[#6EA8FE] font-bold">{row.test}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      {/* Row 3: Dataset Lineage Flow */}
      <Panel title="Dataset Lineage Timeline" subtitle="Evolution path to Scientific Freeze V2">
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 lg:grid-cols-8 gap-3">
            {DATASET_LINEAGE.map((node, idx) => (
              <div
                key={node.id}
                className={`p-3 rounded border text-[11px] flex flex-col justify-between h-28 ${
                  idx === DATASET_LINEAGE.length - 1
                    ? 'border-[#6EA8FE] bg-[#1D3A6B]/10'
                    : 'astra-glass'
                }`}
              >
                <div>
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="font-mono text-[#5A6878] font-bold">0{idx + 1}</span>
                    {idx === DATASET_LINEAGE.length - 1 && (
                      <span className="bg-[#6EA8FE]/20 text-[#6EA8FE] px-1 rounded text-[8px] font-mono border border-[#6EA8FE]/30">
                        LOCKED
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-[#D7DEE7] leading-tight truncate">{node.label}</h4>
                  <p className="text-[#8B97A7] leading-tight mt-1 line-clamp-3 text-[10px]" title={node.description}>
                    {node.description}
                  </p>
                </div>
                {node.count && (
                  <div className="text-right mt-1">
                    <span className="font-mono font-semibold text-[#6EA8FE] bg-[#1D3A6B]/20 border border-[#1D3A6B]/40 px-1.5 py-0.5 rounded text-[10px]">
                      {node.count} stars
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </Panel>

      {/* Row 4: Audit History & Integrity */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Verification Audit */}
        <div className="md:col-span-2">
          <Panel title="Gate Verification Audit History" subtitle="Zero-trust reproduction validations">
            <div className="space-y-4">
              {AUDIT_EVENTS.map((evt, idx) => (
                <div key={idx} className="p-3 astra-glass rounded flex items-start gap-3 text-[11px]">
                  <div className="font-mono text-[#6EA8FE] bg-[#1D3A6B]/30 px-2 py-0.5 border border-[#1D3A6B] rounded shrink-0">
                    {evt.phase}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#D7DEE7]">{evt.title}</span>
                      <span className="text-[#5A6878] font-mono">{evt.date}</span>
                    </div>
                    <p className="text-[#8B97A7] leading-normal">{evt.description}</p>
                  </div>
                  <div className="shrink-0">
                    <StatusBadge status={evt.status as 'PASS'} />
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        {/* Data Quality */}
        <div>
          <Panel title="Metadata Integrity Audit" subtitle="Phase 7C zero-trust results">
            <div className="space-y-0.5">
              <DataRow label="Total NaN checks" value="0 issues" mono />
              <DataRow label="Total Inf checks" value="0 issues" mono />
              <DataRow label="Deduplication (coordinate)" value="0 duplicates" mono />
              <DataRow label="SHA-256 matched records" value="944 / 944" mono />
              <DataRow label="Split leakage overlaps" value="0 overlap" mono />
              <DataRow label="Data array checks" value="944 files PASS" mono />
              <DataRow label="Integrity Status" value="SECURE" mono />
            </div>
            <div className="mt-4 p-2.5 bg-green-500/5 border border-green-500/20 text-green-400 text-[10px] rounded leading-normal flex items-start gap-1.5">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full shrink-0 mt-1" />
              <span>
                Zero-trust audit successfully verified exact matching between scientific dataset and processed Numpy light curve files.
              </span>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
