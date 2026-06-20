import { apiClient } from './client';
import { Material, MaterialDetail } from '../types/index';

export const listMaterials = (params: { dataset_id?: string; skip?: number; limit?: number }) =>
  apiClient.get<Material[]>('/materials', { params });

export const getMaterial = (id: string) =>
  apiClient.get<MaterialDetail>(`/materials/${id}`);

export const getHullData = (datasetId: string) =>
  apiClient.get<{ points: import('../types/index').HullPoint[] }>(`/materials/dataset/${datasetId}/hull-data`);

export const getMaterialAnalysis = (materialId: string) =>
  apiClient.get<import('../types/index').MaterialAnalysis>(`/materials/${materialId}/analysis`);

export const getMaterialStructure = (materialId: string) =>
  apiClient.get<import('../types/index').CrystalStructure>(`/materials/${materialId}/structure`);

export const getMaterialDecomposition = (materialId: string) =>
  apiClient.get<import('../types/index').DecompositionData>(`/materials/${materialId}/decomposition`);
