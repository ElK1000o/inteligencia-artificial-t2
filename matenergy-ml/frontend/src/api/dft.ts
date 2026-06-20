import { apiClient } from './client';

export interface DftJobResult {
  total_energy: number | null;
  formation_energy: number | null;
  energy_above_hull: number | null;
  band_gap: number | null;
  is_magnetic: boolean | null;
  source: string | null;
  calculator: string | null;
  n_atoms: number | null;
  warning: string | null;
}

export interface DftJob {
  id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  formula: string | null;
  calculation_type: string | null;
  adapter: string | null;
  job_name: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  progress_pct: number | null;
  error_message: string | null;
  result: DftJobResult | null;
}

export interface DftSubmitPayload {
  formula: string;
  structure_json?: object | null;
  calculation_type: string;
  functional: string;
  encut: number;
  kpoints_density: number;
  hubbard_u: Record<string, number>;
  adapter: string;
  job_name?: string | null;
}

export interface DftIngestPayload {
  material_id: string;
}

export const submitDftJob = (payload: DftSubmitPayload) =>
  apiClient.post<DftJob>('/dft-jobs', payload);

export const listDftJobs = (params?: { skip?: number; limit?: number }) =>
  apiClient.get<DftJob[]>('/dft-jobs', { params });

export const getDftJob = (jobId: string) =>
  apiClient.get<DftJob>(`/dft-jobs/${jobId}`);

export const cancelDftJob = (jobId: string) =>
  apiClient.delete(`/dft-jobs/${jobId}`);

export const ingestDftResults = (jobId: string, payload: DftIngestPayload) =>
  apiClient.post(`/dft-jobs/${jobId}/ingest`, payload);
