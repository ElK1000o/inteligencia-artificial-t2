import { apiClient } from './client';
import { Dataset, ValidationReport } from '../types';

export const listDatasets = (skip = 0, limit = 50) =>
  apiClient.get<Dataset[]>('/datasets', { params: { skip, limit } });

export const getDataset = (id: string) =>
  apiClient.get<Dataset>(`/datasets/${id}`);

export const uploadDataset = (file: File, name: string, description?: string) => {
  const form = new FormData();
  form.append('file', file);
  form.append('name', name);
  if (description) form.append('description', description);
  return apiClient.post<Dataset>('/datasets/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getValidationReport = (datasetId: string) =>
  apiClient.get<ValidationReport>(`/datasets/${datasetId}/validation-report`);
