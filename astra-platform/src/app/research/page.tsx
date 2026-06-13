'use client';

import { MetricCard, Panel } from '@/components/shared/UI';
import { useResearchFindings, useCalibrationDetails } from '@/lib/hooks';
import { CLASS_LABELS, CLASS_COLORS, formatPercent } from '@/lib/utils';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from 'recharts';

export default function ResearchFindingsPage() {
  const { data: researchData, isLoading: researchLoading } = useResearchFindings();
  const { data: calibrationData, isLoading: calibrationLoading } = useCalibrationDetails();

  if (researchLoading || calibrationLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-[#D7DEE7]">Research Findings</h1>
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5 animate-pulse">
            Loading research metrics and uncertainty coverage sweeps…
          </p>
        </div>
        <div className="h-64 astra-glass rounded animate-pulse" />
      </div>
    );
  }

  if (!researchData || !calibrationData) {
    return (
      <div className="p-6 text-center text-red-400 font-mono border border-red-500/20 bg-red-950/10 rounded">
        System Error: Failed to retrieve dynamic research findings.
      </div>
    );
  }

  const findings = researchData.findings;
  const uncertainty = researchData.uncertainty;
  const sharedTransformer = findings.shared_transformer;
  const subgroups = sharedTransformer.subgroups;

  // Chart data for class performance F1 scores
  const classF1Data = Object.entries(sharedTransformer.per_class_f1).map(([key, val]) => ({
    name: CLASS_LABELS[key as keyof typeof CLASS_LABELS] || key,
    f1: val as number,
    color: CLASS_COLORS[key as keyof typeof CLASS_COLORS] || '#6B7280',
  }));

  // Line chart formatting from uncertainty coverage sweep
  const thresholds = [0.5, 0.6, 0.7, 0.8, 0.9];
  const sweep = uncertainty.coverage_sweep || [];
  const lineData = thresholds.map((t) => {
    const cnnItem = sweep.find((d: any) => d.model === 'cnn_dual' && Math.abs(d.confidence_threshold - t) < 0.01);
    const transItem = sweep.find((d: any) => d.model === 'shared' && Math.abs(d.confidence_threshold - t) < 0.01);
    
    return {
      threshold: t.toFixed(1),
      'CNN Dual Branch': cnnItem ? cnnItem.accuracy * 100 : 0,
      'Transformer Shared': transItem ? transItem.accuracy * 100 : 0,
      'CNN Coverage': cnnItem ? cnnItem.coverage * 100 : 0,
      'Transformer Coverage': transItem ? transItem.coverage * 100 : 0,
    };
  });

  const calibrationRows = [
    {
      name: 'CNN Dual Branch',
      raw: calibrationData.global.cnn_dual.ece_raw,
      calibrated: calibrationData.global.cnn_dual.ece_calibrated,
      temp: calibrationData.temperatures.cnn_dual,
    },
    {
      name: 'Transformer Shared',
      raw: calibrationData.global.shared.ece_raw,
      calibrated: calibrationData.global.shared.ece_calibrated,
      temp: calibrationData.temperatures.shared,
    }
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-semibold text-[#D7DEE7]">Research Findings</h1>
        <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5">
          Period Estimation Quality as the Primary Performance Bottleneck
        </p>
        <p className="text-[10px] text-[#5A6878] font-mono mt-1">
          Phase 7C Ground Truth Audit · June 2026
        </p>
      </div>

      {/* Main Discovery Banner */}
      <div className="p-4 astra-glass !border-l-2 !border-l-[#6EA8FE] rounded-r space-y-2 leading-relaxed">
        <p className="text-[10px] font-mono text-[#6EA8FE] uppercase tracking-wider">Scientific Breakthrough</p>
        <p className="text-[#D7DEE7] text-sm">
          ASTRA performs strongly on catalog-validated periods, achieving{' '}
          <span className="text-emerald-400 font-bold">{(subgroups.catalog_accuracy * 100).toFixed(1)}%</span> classification accuracy on the test subgroup. However, when periods are
          estimated using the Box-Least Squares (BLS) algorithm — applied to stars without catalog matches — accuracy
          drops to <span className="text-amber-500 font-bold">{(subgroups.bls_accuracy * 100).toFixed(1)}%</span>.
        </p>
        <p className="text-[#8B97A7] text-[11px]">
          This suggests that period estimation quality, rather than model architecture, is the dominant factor limiting
          classification performance on this dataset.
        </p>
      </div>

      {/* Performance Gap Column */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Panel title="Catalog-Validated Period Subgroup" subtitle="Stars with periods verified by external catalogs">
          <div className="p-4 rounded border border-green-500/20 bg-green-500/5 space-y-3 font-mono text-[11px]">
            <div className="flex justify-between items-baseline">
              <span className="text-[#8B97A7] font-sans">Accuracy</span>
              <span className="text-xl font-bold text-green-400">{formatPercent(subgroups.catalog_accuracy)}</span>
            </div>
            <div className="flex justify-between items-baseline border-t border-[#1A2430] pt-2">
              <span className="text-[#8B97A7] font-sans">Macro F1 Score</span>
              <span className="text-[#D7DEE7]">{subgroups.catalog_macro_f1.toFixed(4)}</span>
            </div>
            <div className="flex justify-between items-baseline border-t border-[#1A2430] pt-2">
              <span className="text-[#8B97A7] font-sans">Subgroup Count</span>
              <span className="text-[#D7DEE7]">90 stars</span>
            </div>
          </div>
        </Panel>

        <Panel title="BLS-Estimated Period Subgroup" subtitle="Stars with periods auto-computed via BLS search">
          <div className="p-4 rounded border border-yellow-500/20 bg-yellow-500/5 space-y-3 font-mono text-[11px]">
            <div className="flex justify-between items-baseline">
              <span className="text-[#8B97A7] font-sans">Accuracy</span>
              <span className="text-xl font-bold text-amber-500">{formatPercent(subgroups.bls_accuracy)}</span>
            </div>
            <div className="flex justify-between items-baseline border-t border-[#1A2430] pt-2">
              <span className="text-[#8B97A7] font-sans">Macro F1 Score</span>
              <span className="text-[#D7DEE7]">{subgroups.bls_macro_f1.toFixed(4)}</span>
            </div>
            <div className="flex justify-between items-baseline border-t border-[#1A2430] pt-2">
              <span className="text-[#8B97A7] font-sans">Subgroup Count</span>
              <span className="text-[#D7DEE7]">52 stars</span>
            </div>
          </div>
        </Panel>
      </div>

      {/* Row 4: Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Per Class F1 scores */}
        <Panel title="Per-Class F1 Performance" subtitle="Accuracy representation per verified target class">
          <div className="h-64 flex flex-col justify-between">
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={classF1Data} margin={{ left: -10, right: 10, top: 10, bottom: 5 }}>
                  <XAxis dataKey="name" stroke="#5A6878" tick={{ fontSize: 9 }} tickLine={false} />
                  <YAxis
                    stroke="#5A6878"
                    tick={{ fontSize: 9 }}
                    domain={[0, 1]}
                    tickFormatter={(v) => v.toFixed(1)}
                    axisLine={false}
                    tickLine={false}
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
                  <Bar dataKey="f1" radius={[2, 2, 0, 0]}>
                    {classF1Data.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 text-[11px] text-[#5A6878] font-sans leading-normal">
              Note: Solar-like and Stable classes show the weakest performance due to low SNR in TESS sectors.
            </div>
          </div>
        </Panel>

        {/* Selective Prediction Analysis */}
        <Panel
          title="Selective Prediction Analysis"
          subtitle="Model accuracy and coverage at varying confidence thresholds"
        >
          <div className="h-64 flex flex-col justify-between">
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lineData} margin={{ left: -10, right: 10, top: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke="#1A2430" />
                  <XAxis dataKey="threshold" stroke="#5A6878" tick={{ fontSize: 9 }} />
                  <YAxis stroke="#5A6878" tick={{ fontSize: 9 }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      background: '#0C1118',
                      border: '1px solid #1A2430',
                      borderRadius: 2,
                      fontSize: 11,
                      color: '#D7DEE7',
                    }}
                  />
                  <Legend verticalAlign="top" height={32} iconSize={10} wrapperStyle={{ fontSize: 10 }} />
                  <Line type="monotone" dataKey="CNN Dual Branch" stroke="#6EA8FE" strokeWidth={1.5} dot />
                  <Line type="monotone" dataKey="Transformer Shared" stroke="#A78BFA" strokeWidth={1.5} dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 text-[11px] text-[#5A6878] font-sans leading-normal">
              At threshold 0.9, coverage drops to ~43% of total dataset but class accuracy reaches{' '}
              <span className="text-[#6EA8FE] font-bold">~98.4%</span>.
            </div>
          </div>
        </Panel>
      </div>

      {/* Calibration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Panel title="Calibration Comparison" subtitle="ECE comparison before and after temperature scaling">
          <div className="overflow-x-auto text-[11px]">
            <table className="w-full text-left text-[#D7DEE7]">
              <thead>
                <tr className="border-b border-[#1A2430] bg-[#05070B]/50">
                  <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider">Architecture</th>
                  <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Raw ECE</th>
                  <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Calibrated ECE</th>
                  <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Scaling Factor (T)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1A2430] font-mono">
                {calibrationRows.map((row, idx) => (
                  <tr key={idx}>
                    <td className="px-3 py-2.5 font-sans font-medium text-[#D7DEE7]">{row.name}</td>
                    <td className="px-3 py-2.5 text-right text-amber-500">{formatPercent(row.raw)}</td>
                    <td className="px-3 py-2.5 text-right text-emerald-400">{formatPercent(row.calibrated)}</td>
                    <td className="px-3 py-2.5 text-right text-[#8B97A7]">T = {row.temp.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Scientific Implications" subtitle="Takeaways from zero-trust audit findings">
          <ul className="list-disc pl-4 space-y-1.5 text-[11px] text-[#8B97A7] leading-relaxed">
            <li>
              <strong className="text-[#D7DEE7]">Period Noise Propagation:</strong> BLS period errors act as spatial input translation noise, destroying phase coherence in folded branch embeddings.
            </li>
            <li>
              <strong className="text-[#D7DEE7]">Uncertainty Weighting:</strong> Targets lacking validated catalog periods should be automatically penalised in prior confidence outputs.
            </li>
            <li>
              <strong className="text-[#D7DEE7]">Selective prediction:</strong> Adopting a threshold filter of ≥0.8 maintains an accuracy level of &gt;93% across 63% of the test pool.
            </li>
            <li>
              <strong className="text-[#D7DEE7]">Future Iterations:</strong> Incorporating multi-epoch Lomb-Scargle or neural-network based period search should be prioritized over model parameter tuning.
            </li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}
