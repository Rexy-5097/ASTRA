export type AstraClass = 'rr_lyrae' | 'cepheid' | 'eclipsing_binary' | 'solar_like' | 'stable';
export type PeriodSource = 'catalog' | 'BLS';
export type Split = 'train' | 'val' | 'test';

export interface SectorInfo {
  mission: string;
  author: string;
  exptime: number;
  target_name: string;
  sequence_number: number;
}

export interface Star {
  tic_id: number;
  astra_class: AstraClass;
  ra: number;
  dec: number;
  period: number;
  period_source: PeriodSource;
  cadence_type: string;
  preprocessing_version: string;
  split: Split;
  n_sectors: number;
  n_points_raw: number;
  n_points_clean: number;
  bls_period: number | null;
  catalog_period: number | null;
  bls_power: number | null;
  variability_amplitude: number | null;
  snr_estimate: number | null;
  source_catalogs: string[];
  primary_source: string | null;
  catalog_label: string | null;
  sector_information: SectorInfo[];
  source_pipeline: string | null;
  processing_timestamp: string | null;
  preprocessing_hash: string | null;
  has_folded_lc: boolean;
}

export interface LightCurveData {
  tic_id: number;
  flux_1000: number[];
  flux_200: number[];
  folded_flux_1000: number[];
  folded_flux_200: number[];
}

export interface ClassProbabilities {
  rr_lyrae: number;
  cepheid: number;
  eclipsing_binary: number;
  solar_like: number;
  stable: number;
}

export interface ModelPrediction {
  tic_id: number;
  predicted_class: AstraClass;
  true_class: AstraClass;
  probabilities: ClassProbabilities;
  calibrated_probabilities: ClassProbabilities;
  entropy: number;
  confidence: number;
  calibrated_confidence: number;
  is_correct: boolean;
  period_source: PeriodSource;
}

export interface SystemMetrics {
  dataset: {
    total_stars: number;
    freeze_date: string;
    manifest_sha256: string;
    classes: Record<AstraClass, number>;
    period_sources: Record<PeriodSource, number>;
    splits: { train: number; val: number; test: number };
  };
  model: {
    name: string;
    version: string;
    architecture: string;
    parameters: number;
    checkpoint_hash: string;
    training_date: string;
  };
  performance: {
    val_accuracy: number;
    test_accuracy: number;
    macro_f1: number;
    weighted_f1: number;
    ece_before: number;
    ece_after: number;
    calibration_temperature: number;
    bootstrap_ci_accuracy: [number, number];
    bootstrap_ci_macro_f1: [number, number];
    per_class_f1: Record<AstraClass, number>;
  };
  subgroup: {
    catalog: { accuracy: number; count: number; macro_f1: number; ece: number };
    bls: { accuracy: number; count: number; macro_f1: number; ece: number };
  };
}

export interface CheckpointRecord {
  filename: string;
  architecture: string;
  loaded_params: number;
  expected_params: number;
  missing_keys: number;
  unexpected_keys: number;
  sha256: string;
  val_accuracy?: number;
  test_accuracy?: number;
  macro_f1?: number;
}

export interface DatasetLineageNode {
  id: string;
  label: string;
  description: string;
  count?: number;
  date?: string;
}

export interface StarsResponse {
  stars: Star[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

