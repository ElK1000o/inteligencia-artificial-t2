export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  roles: string[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  sha256_hash: string;
  row_count: number | null;
  valid_row_count: number | null;
  rejected_row_count: number | null;
  status: string;
  available_properties: string[] | null;
  imported_at: string | null;
  imported_by: string;
}

export interface Material {
  id: string;
  formula: string;
  reduced_formula: string | null;
  chemsys: string | null;
  nelements: number | null;
  elements: string[] | null;
  dataset_id: string;
  created_at: string | null;
}

export interface MaterialDetail extends Material {
  properties: MaterialProperty[];
}

export interface MaterialProperty {
  property_name: string;
  value_float: number | null;
  value_str: string | null;
  unit: string | null;
  is_dft_computed: boolean;
}

export interface ModelVersion {
  id: string;
  name: string;
  model_type: string;
  task_type: string;
  target_property: string;
  is_active: boolean;
  version_tag: string | null;
  created_at: string;
}

export interface ModelMetric {
  split: string;
  metric_name: string;
  metric_value: number;
}

export interface Prediction {
  id: string;
  material_id: string;
  predicted_value: number | null;
  predicted_class: string | null;
  confidence_score: number | null;
  is_out_of_domain: boolean;
  out_of_domain_reason: string | null;
  created_at: string;
}

export interface CandidateRanking {
  id: string;
  name: string;
  application_target: string;
  n_candidates: number | null;
  created_at: string;
}

export interface RankingItem {
  material_id: string;
  rank_position: number;
  candidate_score: number;
  priority_label: string;
  reasoning_summary: string;
  stability_score: number | null;
  uncertainty_penalty: number | null;
  is_out_of_domain: boolean;
}

export interface DashboardStats {
  total_materials: number;
  valid_materials: number;
  rejected_rows: number;
  active_datasets: number;
  active_models: number;
  best_mae: number | null;
  best_f1: number | null;
  stable_candidates: number;
  last_training: string | null;
  security_events_count: number;
}

export interface DescriptorSet {
  id: string;
  name: string;
  version: string;
  descriptor_type: string;
  n_features: number | null;
  created_at: string;
}

export interface ValidationReport {
  id: string;
  dataset_id: string;
  total_rows: number | null;
  valid_rows: number | null;
  rejected_rows: number | null;
  validation_errors: Record<string, unknown> | null;
  warnings: string[] | null;
  validated_at: string | null;
}

export interface ApiError {
  error: string;
  message: string;
  recommended_action?: string;
}

export interface HullPoint {
  material_id: string;
  formula: string;
  formation_energy_per_atom: number | null;
  energy_above_hull: number | null;
  stability_label: 'stable' | 'metastable' | 'unstable' | 'unknown';
}

export interface SpaceMapPoint {
  material_id: string;
  formula: string;
  x: number;
  y: number;
  z: number | null;
  color_value: number | null;
  color_property: string;
}

export interface ElementData {
  symbol: string;
  amount: number;
  fraction: number;
  atomic_radius: number | null;
  electronegativity: number | null;
  common_oxidation_states: number[];
  period: number;
  group: number;
  block: string;
}

export interface InstabilityFactor {
  factor: string;
  severity: 'low' | 'medium' | 'high';
  value: number | null;
  unit: string | null;
  explanation: string;
  threshold_note?: string;
}

export interface CrystalSite {
  element: string;
  frac_coords: [number, number, number];
  cart_coords: [number, number, number];
}

export interface CoordinationInfo {
  element: string;
  site_index: number;
  cn: number | null;
  neighbor_elements: string[];
}

export interface BondInfo {
  pair: string;
  mean_ang: number;
  std_ang: number;
  min_ang: number;
  max_ang: number;
  n_bonds: number;
}

export interface CrystalStructure {
  mp_material_id: string;
  formula: string;
  energy_above_hull: number | null;
  cif: string;
  n_sites: number;
  n_species: number;
  lattice: {
    a: number; b: number; c: number;
    alpha: number; beta: number; gamma: number;
    volume: number;
  };
  density: number;
  space_group: string;
  space_group_number: number;
  crystal_system: string;
  sites: CrystalSite[];
  coordination: CoordinationInfo[];
  bond_analysis: BondInfo[];
  n_polymorphs: number;
  structure_source: string;
}

export interface DecompositionProduct {
  formula: string;
  fraction: number;
  mp_id: string | null;
}

export interface DecompositionData {
  formula: string;
  reduced_formula: string;
  chemsys: string;
  energy_above_hull: number;
  decomposition_products: DecompositionProduct[];
  decomposition_reaction: string;
  is_stable: boolean;
  n_pd_entries: number;
  not_in_mp: boolean;
  source: string;
}

export interface MaterialAnalysis {
  formula: string;
  reduced_formula: string | null;
  element_data: ElementData[];
  composition_stats: {
    n_elements: number;
    electronegativity_spread: number;
    electronegativity_mean: number;
    size_mismatch_ratio: number;
    charge_balanced: boolean | null;
    dominant_oxidation_states: Record<string, number>;
  };
  dft_properties: {
    energy_above_hull: number | null;
    formation_energy_per_atom: number | null;
    band_gap: number | null;
  };
  instability_factors: InstabilityFactor[];
  stability_verdict: 'stable' | 'metastable' | 'unstable' | 'unknown';
  verdict_text: string;
  verdict_detail: string;
  structure_note: string;
}
