import { apiClient } from './client';

export interface ReportFileInfo {
  filename: string;
  size_bytes: number;
  content_type: string;
}

export interface GeneratedReport {
  report_type: string;
  file_path: string;
  filename: string;
  content_type: string;
  size_bytes: number;
}

export const generateReport = (reportType: string, resourceId?: string) =>
  apiClient.post<GeneratedReport>('/reports/generate', {
    report_type: reportType,
    resource_id: resourceId || null,
  });

export const listReports = (skip = 0, limit = 50) =>
  apiClient.get<ReportFileInfo[]>('/reports', { params: { skip, limit } });

export const downloadReport = (filename: string) =>
  apiClient.get(`/reports/${filename}`, { responseType: 'blob' });
