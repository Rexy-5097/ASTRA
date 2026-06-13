import type { SystemMetrics, CheckpointRecord, AstraClass } from '../types';

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

export const SYSTEM_METRICS: SystemMetrics = {
  dataset: {
    total_stars: 944,
    freeze_date: '2026-06-12',
    manifest_sha256: 'f99b4b06f16952033b5445bb0682d059e9ea4c3f99320a05d31aebb25c2dbf58',
    classes: { rr_lyrae: 217, cepheid: 230, eclipsing_binary: 150, solar_like: 142, stable: 205 },
    period_sources: { catalog: 597, BLS: 347 },
    splits: { train: 661, val: 141, test: 142 },
  },
  model: {
    name: 'ASTRA-TRANS-SHARED',
    version: 'v2.0.0-phase7b',
    architecture: 'HybridTransformer (shared)',
    parameters: 1373701,
    checkpoint_hash: 'bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388',
    training_date: '2026-06-13',
  },
  performance: {
    val_accuracy: 0.8582,
    test_accuracy: 0.7817,
    macro_f1: 0.7677,
    weighted_f1: 0.7784,
    ece_before: 0.0810,
    ece_after: 0.0442,
    calibration_temperature: 1.257665,
    bootstrap_ci_accuracy: [0.7113, 0.8521],
    bootstrap_ci_macro_f1: [0.6944, 0.8320],
    per_class_f1: { rr_lyrae: 0.9394, cepheid: 0.8108, eclipsing_binary: 0.9091, solar_like: 0.5238, stable: 0.6552 },
  },
  subgroup: {
    catalog: { accuracy: 0.9000, count: 90, macro_f1: 0.5602, ece: 0.0467 },
    bls: { accuracy: 0.5769, count: 52, macro_f1: 0.3170, ece: 0.1465 },
  },
};

export const CHECKPOINT_REGISTRY: CheckpointRecord[] = [
  { filename: 'best_star_cnn_dual_aug.pt', architecture: 'CNN Dual Branch', loaded_params: 1047312, expected_params: 1043333, missing_keys: 0, unexpected_keys: 0, sha256: '65da1034868c5460b2c269e1a11936864fe6191fa81116d5fe2be934d8478af2', val_accuracy: 0.8511, test_accuracy: 0.7817, macro_f1: 0.7635 },
  { filename: 'best_star_transformer_shared.pt', architecture: 'Transformer Shared', loaded_params: 1377680, expected_params: 1373701, missing_keys: 0, unexpected_keys: 0, sha256: 'bf374ce492825916f2f97a4e29673a1eca35f76cc08f603b384d103fbe95d388', val_accuracy: 0.8582, test_accuracy: 0.7817, macro_f1: 0.7677 },
  { filename: 'best_star_transformer_cross.pt', architecture: 'Transformer Cross', loaded_params: 1244944, expected_params: 1240965, missing_keys: 0, unexpected_keys: 0, sha256: '9d90b14be3b9f4437e0a289810034506734a969c47ccdeae440d420291925a23' },
  { filename: 'best_star_transformer_separate.pt', architecture: 'Transformer Separate', loaded_params: 1691536, expected_params: 1687557, missing_keys: 0, unexpected_keys: 0, sha256: '0189295d56641331b8074f18d4395a1bbd204cfac61bf56861ee5a294d933851' },
  { filename: 'best_star_transformer_only.pt', architecture: 'Transformer Only', loaded_params: 317446, expected_params: 316933, missing_keys: 0, unexpected_keys: 0, sha256: '8f66b566c408e56df60f42068b2f5710e75f45722650e3befd770be4cd64df1c' },
  { filename: 'best_star_cnn_raw_aug.pt', architecture: 'CNN Raw Augmented', loaded_params: 1144140, expected_params: 1140101, missing_keys: 0, unexpected_keys: 0, sha256: 'e70220a7e479fd88a873604cb120a5125d79a2bd31f66ce1da07f04180f3e564' },
  { filename: 'best_star_transformer_shared_no_folded.pt', architecture: 'Transformer Shared (no fold)', loaded_params: 1279120, expected_params: 1275141, missing_keys: 0, unexpected_keys: 0, sha256: '66ab7ac32634f0b8177a17146b25e80619cccd9e7ebabbf4b28be1ac2da4a96f' },
  { filename: 'best_star_transformer_shared_no_folded_matched.pt', architecture: 'Transformer Shared (no fold matched)', loaded_params: 1327704, expected_params: 1324089, missing_keys: 0, unexpected_keys: 0, sha256: 'ff39f8b53d89e796f2a1a7846a68f8c250a490d400cc2887bd363771480a8f98' },
  { filename: 'best_star_cnn.pt', architecture: 'CNN (legacy)', loaded_params: 1144140, expected_params: 1043333, missing_keys: 0, unexpected_keys: 0, sha256: '02eb0d39ee86d421bf7e9421f839ba142c442375b7ab045e42487bf932e93aea' },
];

export const DATASET_LINEAGE = [
  { id: 'source-catalogs', label: 'Source Catalogs', description: 'VSX, ASAS-SN, GCVS, 2MASS, Gaia DR3 cross-matched candidates', count: 3200 },
  { id: 'candidate-pool', label: 'Initial Candidate Pool', description: 'TIC targets with known variability classifications from cross-matching', count: 2847 },
  { id: 'tess-filtering', label: 'TESS Availability Filter', description: 'Filtered to targets with confirmed TESS photometric coverage ≥1 sector', count: 1621 },
  { id: 'quality-filter', label: 'Quality & Deduplication', description: 'SNR thresholding, coordinate deduplication (2 arcsec), period quality gates', count: 1102 },
  { id: 'phase6-freeze', label: 'Phase 6 Initial Freeze', description: 'First scientific freeze with preprocessing v1. Metadata verified.', count: 978 },
  { id: 'metadata-repair', label: 'Metadata Repair (Phase 6.5)', description: 'Period source re-classification, BLS re-estimation for missing catalog periods', count: 978 },
  { id: 'class-rebalance', label: 'Class Rebalancing', description: 'Stable class expansion via relaxed SNR threshold. Coordinated with metadata v2.', count: 944 },
  { id: 'scientific-freeze-v2', label: 'Scientific Freeze V2', description: 'Final 944-star frozen dataset. SHA256 locked. Phase 7C verified.', count: 944 },
];

export const AUDIT_EVENTS = [
  { phase: 'Phase 7A', title: 'Pre-Training Verification Gate', status: 'PASS', date: '2026-06-12', description: 'Split integrity, class balance, period balance, array integrity, and model sanity checks.' },
  { phase: 'Phase 7B', title: 'Large-Scale Retraining and Benchmark Suite', status: 'PASS', date: '2026-06-13', description: 'CNN Dual Branch and Transformer Shared retrained from scratch with SEED=42 determinism.' },
  { phase: 'Phase 7C', title: 'Ground Truth Verification Audit', status: 'PASS', date: '2026-06-13', description: 'Zero-trust recomputation of all metrics, hashes, calibration, and uncertainty parameters. 0 mismatches.' },
];

export const SELECTIVE_PREDICTION_DATA = [
  { threshold: 0.5, cnn_accuracy: 0.7817, trans_accuracy: 0.7817, cnn_coverage: 1.0, trans_coverage: 1.0 },
  { threshold: 0.6, cnn_accuracy: 0.825, trans_accuracy: 0.831, cnn_coverage: 0.88, trans_coverage: 0.89 },
  { threshold: 0.7, cnn_accuracy: 0.874, trans_accuracy: 0.885, cnn_coverage: 0.75, trans_coverage: 0.76 },
  { threshold: 0.8, cnn_accuracy: 0.925, trans_accuracy: 0.938, cnn_coverage: 0.61, trans_coverage: 0.62 },
  { threshold: 0.9, cnn_accuracy: 0.985, trans_accuracy: 0.991, cnn_coverage: 0.44, trans_coverage: 0.45 },
];

export const PER_CLASS_ECE = [
  { class: 'rr_lyrae', before: 0.052, after: 0.021 },
  { class: 'cepheid', before: 0.075, after: 0.038 },
  { class: 'eclipsing_binary', before: 0.048, after: 0.019 },
  { class: 'solar_like', before: 0.124, after: 0.062 },
  { class: 'stable', before: 0.106, after: 0.051 },
];
