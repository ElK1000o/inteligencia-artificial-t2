import { apiClient } from './client';
import { CandidateRanking, RankingItem } from '../types';

export const listRankings = () => apiClient.get<CandidateRanking[]>('/rankings');

export const getRankingItems = (rankingId: string) =>
  apiClient.get<{ items: RankingItem[] }>(`/rankings/${rankingId}`);

export const createRanking = (payload: {
  name: string;
  application_target: string;
  dataset_id: string;
  weights?: Record<string, number>;
}) => apiClient.post<CandidateRanking>('/rankings', payload);
