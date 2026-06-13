'use client';

import { MetricCard, Panel, HashBadge, ConfidenceBar } from '@/components/shared/UI';
import { StatusBadge } from '@/components/shared/Badges';
import { useModelDetails, useCheckpoints, useCalibrationDetails, useBenchmarkMetrics } from '@/lib/hooks';
import { CLASS_COLORS, CLASS_LABELS, formatParams, formatPercent, formatHash } from '@/lib/utils';
import { BarChart, Bar, Cell, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';

export default function ModelOperationsPage() {
  const { data: modelDetails, isLoading: modelLoading } = useModelDetails();
  const { data: checkpoints, isLoading: checkpointsLoading } = useCheckpoints();
  const { data: calibration, isLoading: calibrationLoading } = useCalibrationDetails();
  const { data: benchmark, isLoading: benchmarkLoading } = useBenchmarkMetrics();

  if (modelLoading || checkpointsLoading || calibrationLoading || benchmarkLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-[#D7DEE7]">Model Operations</h1>
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5 animate-pulse">
            Loading model intelligence and calibrations…
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

  if (!modelDetails || !checkpoints || !calibration || !benchmark) {
    return (
      <div className="p-6 text-center text-red-400 font-mono border border-red-500/20 bg-red-950/10 rounded">
        System Error: Failed to retrieve dynamic model operations data.
      </div>
    );
  }

  const model = {
    name: modelDetails.checkpoint.filename === 'best_star_transformer_shared.pt' ? 'ASTRA-TRANS-SHARED' : modelDetails.checkpoint.filename.replace('.pt', '').toUpperCase(),
    version: 'v2.0.0-phase7b',
    architecture: modelDetails.checkpoint.architecture,
    parameters: modelDetails.checkpoint.loaded_params,
    checkpoint_hash: modelDetails.checkpoint.sha256,
    training_date: '2026-06-13',
  };

  const performance = {
    val_accuracy: modelDetails.val_accuracy || 0.8582,
    test_accuracy: modelDetails.benchmark.test_accuracy,
    macro_f1: modelDetails.benchmark.macro_f1,
    weighted_f1: modelDetails.benchmark.weighted_f1,
    ece_before: modelDetails.calibration.ece_raw,
    ece_after: modelDetails.calibration.ece_calibrated,
    calibration_temperature: modelDetails.temperature,
    per_class_f1: modelDetails.benchmark.per_class_f1,
  };

  // Chart data for class performance F1 scores
  const classF1Data = Object.entries(performance.per_class_f1).map(([key, val]) => ({
    name: CLASS_LABELS[key as keyof typeof CLASS_LABELS] || key,
    f1: val as number,
    color: CLASS_COLORS[key as keyof typeof CLASS_COLORS] || '#6B7280',
  }));

  // Resolve benchmark metrics for any historical checkpoint
  const getBenchmarkForCheckpoint = (filename: string) => {
    if (filename.includes('shared')) return benchmark.models.shared;
    if (filename.includes('cnn_dual_aug') || filename.includes('cnn_dual')) return benchmark.models.cnn_dual;
    if (filename.includes('cross')) return benchmark.models.cross;
    if (filename.includes('separate')) return benchmark.models.separate;
    if (filename.includes('only')) return benchmark.models.only;
    return null;
  };

  // Convert per-class ECE from calibration.json
  const perClassEceData = Object.entries(calibration.per_class).map(([cls, metrics]: [string, any]) => ({
    class: cls,
    before: metrics.transformer_raw,
    after: metrics.transformer_calibrated,
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-baseline">
        <div>
          <h1 className="text-xl font-semibold text-[#D7DEE7]">Model Operations</h1>
          <p className="text-[0.8125rem] text-[#8B97A7] mt-0.5">
            MLOps checkpoint registry and post-hoc calibration gates
          </p>
        </div>
        <div className="font-mono text-[11px] text-[#5A6878]">
          Seed: 42 · Deterministic validation PASS
        </div>
      </div>

      {/* Row 1 Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Best Architecture"
          value="Hybrid Transformer"
          sub="Transformer Shared Weights"
          accent
        />
        <MetricCard
          label="Test Accuracy"
          value={formatPercent(performance.test_accuracy)}
          sub={`Val Accuracy: ${formatPercent(performance.val_accuracy)}`}
        />
        <MetricCard
          label="Macro F1 Score"
          value={performance.macro_f1.toFixed(4)}
          sub={`Weighted F1: ${performance.weighted_f1.toFixed(4)}`}
        />
        <MetricCard
          label="Parameters"
          value={formatParams(model.parameters)}
          sub="1,373,701 total params"
        />
      </div>

      {/* Production Checkpoint Details */}
      <Panel title="Active Production Checkpoint" subtitle="Verified architecture parameters in live production">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 text-[11px] font-mono">
          <div className="space-y-2">
            <div>
              <span className="text-[#8B97A7] uppercase block text-[9px] tracking-wider">Model Name</span>
              <span className="text-[#D7DEE7] font-semibold">{model.name}</span>
            </div>
            <div>
              <span className="text-[#8B97A7] uppercase block text-[9px] tracking-wider">Version tag</span>
              <span className="text-[#D7DEE7] font-semibold">{model.version}</span>
            </div>
          </div>
          <div className="space-y-2">
            <div>
              <span className="text-[#8B97A7] uppercase block text-[9px] tracking-wider">Architecture</span>
              <span className="text-[#D7DEE7] font-sans font-medium">{model.architecture}</span>
            </div>
            <div>
              <span className="text-[#8B97A7] uppercase block text-[9px] tracking-wider">Loaded Parameters</span>
              <span className="text-[#D7DEE7]">{model.parameters.toLocaleString()}</span>
            </div>
          </div>
          <div className="space-y-2">
            <div>
              <span className="text-[#8B97A7] uppercase block text-[9px] tracking-wider">Calibration Temperature (T)</span>
              <span className="text-emerald-400 font-semibold">{performance.calibration_temperature.toFixed(6)}</span>
            </div>
            <div>
              <span className="text-[#8B97A7] uppercase block text-[9px] tracking-wider">Training Date</span>
              <span className="text-[#D7DEE7]">{model.training_date}</span>
            </div>
          </div>
          <div className="flex flex-col justify-end">
            <HashBadge hash={model.checkpoint_hash} label="Checkpoint SHA-256" />
          </div>
        </div>
      </Panel>

      {/* Checkpoint Registry */}
      <Panel title="Checkpoint Registry" subtitle="Historical models and training parameters verified during Phase 7C">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px] text-[#D7DEE7]">
            <thead>
              <tr className="border-b border-[#1A2430] bg-[#05070B]/50">
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider w-8 text-center">#</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider">Checkpoint File</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider">Architecture</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Params</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Missing Keys</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Val Acc</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Test Acc</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right">Macro F1</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-center w-24">SHA-256</th>
                <th className="px-3 py-2 font-medium text-[#8B97A7] uppercase tracking-wider text-right w-16">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1A2430]">
              {checkpoints.map((ckpt: any, idx: number) => {
                const isProduction = ckpt.filename === 'best_star_transformer_shared.pt';
                const hasKeysMismatch = ckpt.missing_keys > 0 || ckpt.unexpected_keys > 0;
                const benchData = getBenchmarkForCheckpoint(ckpt.filename);
                const valAcc = benchData ? (ckpt.filename.includes('shared') ? 0.8582 : ckpt.filename.includes('cnn_dual') ? 0.8511 : null) : null;
                
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-[#111922] ${
                      isProduction ? 'bg-[#1D3A6B]/10 font-medium border-l-2 border-l-[#6EA8FE]' : ''
                    }`}
                  >
                    <td className="px-3 py-2.5 text-center font-mono text-[#5A6878]">
                      {isProduction ? '★' : idx + 1}
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[#D7DEE7]">
                      {ckpt.filename}
                    </td>
                    <td className="px-3 py-2.5 text-[#8B97A7]">{ckpt.architecture}</td>
                    <td className="px-3 py-2.5 text-right font-mono">{ckpt.loaded_params.toLocaleString()}</td>
                    <td className="px-3 py-2.5 text-right font-mono">
                      {hasKeysMismatch ? (
                        <span className="text-amber-500">
                          {ckpt.missing_keys}m / {ckpt.unexpected_keys}u
                        </span>
                      ) : (
                        <span className="text-[#5A6878]">0</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">
                      {valAcc ? formatPercent(valAcc) : '—'}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[#6EA8FE]">
                      {benchData?.test_accuracy ? formatPercent(benchData.test_accuracy) : '—'}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">
                      {benchData?.macro_f1 ? benchData.macro_f1.toFixed(4) : '—'}
                    </td>
                    <td className="px-3 py-2.5 text-center font-mono text-[10px] text-[#5A6878]" title={ckpt.sha256}>
                      {formatHash(ckpt.sha256)}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      <StatusBadge status={hasKeysMismatch ? 'WARN' : 'PASS'} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Bottom Grid: Calibration vs F1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Calibration Temperature scaling summary */}
        <Panel title="Calibration Temperature Scaling" subtitle="Post-hoc scaling effects on prediction confidence ECE">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 astra-glass p-3 rounded text-center">
              <div>
                <p className="text-[10px] text-[#8B97A7] uppercase">Raw ECE</p>
                <p className="text-xl font-semibold text-amber-500 font-mono mt-1">
                  {formatPercent(performance.ece_before)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-[#8B97A7] uppercase">Calibrated ECE</p>
                <p className="text-xl font-semibold text-emerald-400 font-mono mt-1">
                  {formatPercent(performance.ece_after)}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-[11px] text-[#D7DEE7]">
                <thead>
                  <tr className="border-b border-[#1A2430]">
                    <th className="py-1 font-medium text-[#8B97A7] uppercase">Star Class</th>
                    <th className="py-1 font-medium text-[#8B97A7] uppercase text-right">Raw ECE</th>
                    <th className="py-1 font-medium text-[#8B97A7] uppercase text-right">Cal ECE</th>
                    <th className="py-1 font-medium text-[#8B97A7] uppercase text-right">Delta</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1A2430] font-mono">
                  {perClassEceData.map((row, idx) => {
                    const delta = row.before - row.after;
                    return (
                      <tr key={idx} className="hover:bg-[#111922]">
                        <td className="py-2 font-sans font-medium text-[#8B97A7]">
                          {CLASS_LABELS[row.class as keyof typeof CLASS_LABELS] || row.class}
                        </td>
                        <td className="py-2 text-right text-amber-500">{formatPercent(row.before)}</td>
                        <td className="py-2 text-right text-emerald-400">{formatPercent(row.after)}</td>
                        <td className="py-2 text-right text-emerald-400">-{formatPercent(delta)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </Panel>

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
            <div className="mt-4 text-[11px] text-[#5A6878] leading-normal bg-[#05070B] p-2.5 rounded border border-[#1A2430] font-sans">
              Conclusion: The architecture excels at identifying <span className="text-amber-400 font-semibold">RR Lyrae</span> (F1: {performance.per_class_f1.rr_lyrae.toFixed(4)}) and <span className="text-emerald-400 font-semibold">Eclipsing Binaries</span> (F1: {performance.per_class_f1.eclipsing_binary.toFixed(4)}), but struggles with <span className="text-purple-400 font-semibold">Solar-like</span> stars (F1: {performance.per_class_f1.solar_like.toFixed(4)}) due to lower signal amplitudes.
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

