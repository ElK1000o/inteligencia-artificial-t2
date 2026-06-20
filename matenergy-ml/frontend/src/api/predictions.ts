import { apiClient } from './client';
import { Prediction } from '../types';

export interface PredictionBatchResult {
  batch_id: string;
  model_version_id: string;
  n_predicted: number;
  n_ood: number;
  predictions: PredictionResult[];
}

export interface PredictionResult {
  material_id: string;
  predicted_value: number | null;
  predicted_class: string | null;
  confidence_score: number | null;
  is_out_of_domain: boolean;
  out_of_domain_reason: string | null;
  error?: string;
}

export const runPredictions = (payload: {
  target_property: string;
  material_ids: string[];
  dataset_id: string;
  model_version_id?: string;
}) => apiClient.post<PredictionBatchResult>('/predictions/batch', payload);

export const listPredictions = (params?: { batch_id?: string; skip?: number; limit?: number }) =>
  apiClient.get<Prediction[]>('/predictions', { params });
