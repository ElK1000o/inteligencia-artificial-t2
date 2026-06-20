import { apiClient } from './client';
import { ModelVersion, ModelMetric } from '../types';

export const listModels = () => apiClient.get<ModelVersion[]>('/models');

export const getModelMetrics = (modelId: string) =>
  apiClient.get<ModelMetric[]>(`/models/${modelId}/metrics`);

export const getFeatureImportance = (modelId: string, topN = 20) =>
  apiClient.get<{ feature: string; importance: number }[]>(
    `/models/${modelId}/feature-importance`,
    { params: { top_n: topN } }
  );

export const getParityData = (modelId: string) =>
  apiClient.get<{
    y_test: number[];
    y_pred: number[];
    mae: number;
    r2: number;
    target_property: string;
  }>(`/models/${modelId}/parity-data`);

export const explainPrediction = (
  modelId: string,
  payload: { material_id: string; dataset_id: string }
) =>
  apiClient.post<{
    model_id: string;
    material_id: string;
    formula: string;
    base_value: number;
    predicted_value: number;
    target_property: string;
    feature_contributions: { feature: string; shap_value: number; feature_value: number }[];
  }>(`/models/${modelId}/explain`, payload);

export const trainModel = (payload: {
  model_type: string;
  task_type: string;
  target_property: string;
  dataset_id: string;
  descriptor_set_id: string;
  name?: string;
  hyperparameters?: Record<string, unknown>;
}) => apiClient.post('/models/train', payload);

export const activateModel = (modelId: string) =>
  apiClient.post(`/models/${modelId}/activate`);
