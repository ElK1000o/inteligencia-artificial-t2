import { apiClient } from './client';
import { DescriptorSet } from '../types';

export const listDescriptorSets = () =>
  apiClient.get<DescriptorSet[]>('/descriptors/sets');

export const generateDescriptors = (payload: {
  dataset_id: string;
  descriptor_type: string;
  name?: string;
}) => apiClient.post<DescriptorSet>('/descriptors/generate', payload);

export const getSpaceMap = (
  setId: string,
  params: { n_components?: number; perplexity?: number; color_property?: string } = {}
) =>
  apiClient.get<{
    points: import('../types/index').SpaceMapPoint[];
    color_min: number;
    color_max: number;
    color_property: string;
  }>(`/descriptors/sets/${setId}/space-map`, { params });
