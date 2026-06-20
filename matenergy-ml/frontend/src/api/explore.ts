import { apiClient } from './client';

export interface ExploreResult {
  formula: string;
  predictions: Record<string, number | null>;
  stability_label: 'stable' | 'metastable' | 'unstable' | 'unknown';
  is_known_material: boolean;
  material_id: string | null;
  descriptors_preview: Record<string, number>;
}

export const explorePredict = (payload: {
  formula: string;
  descriptor_set_id: string;
  target_properties: string[];
}) => apiClient.post<ExploreResult>('/explore/predict', payload);
