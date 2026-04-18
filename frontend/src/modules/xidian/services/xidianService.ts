import { apiClient } from '@/libs/http/apiClient';

export interface XidianBindingStatus {
  is_bound: boolean;
  username?: string | null;
  is_postgraduate?: boolean | null;
  last_verified_at?: string | null;
  last_sync_at?: string | null;
}

export interface XidianCaptchaChallenge {
  challenge_id: string;
  captcha_big: string;
  captcha_piece: string;
  puzzle_width: number;
  puzzle_height: number;
  piece_width: number;
  piece_height: number;
  piece_y: number;
}

export interface XidianBindCompleteRequest {
  challenge_id: string;
  slider_position: number;
  username?: string;
  password?: string;
}

export interface XidianBindCompleteResponse {
  is_bound: boolean;
  username: string;
  is_postgraduate?: boolean | null;
  last_verified_at?: string | null;
}

export interface XidianSyncResponse {
  data: Record<string, unknown>;
  fetched_at: string;
  is_cached?: boolean;
}

export interface XidianSnapshotResponse {
  data: Record<string, unknown>;
  is_cached: boolean;
  cached_at: string | null;
}

export const xidianService = {
  async getBindingStatus(): Promise<XidianBindingStatus> {
    const response = await apiClient.get<XidianBindingStatus>('/xidian/binding');
    return response.data;
  },

  async startBinding(): Promise<XidianCaptchaChallenge> {
    const response = await apiClient.post<XidianCaptchaChallenge>('/xidian/binding/start');
    return response.data;
  },

  async completeBinding(request: XidianBindCompleteRequest): Promise<XidianBindCompleteResponse> {
    const response = await apiClient.post<XidianBindCompleteResponse>('/xidian/binding/complete', request);
    return response.data;
  },

  async unbind(): Promise<void> {
    await apiClient.post('/xidian/binding/unbind');
  },

  async syncClasstable(): Promise<XidianSyncResponse> {
    const response = await apiClient.post<XidianSyncResponse>('/xidian/sync/classtable');
    return response.data;
  },

  async syncExams(): Promise<XidianSyncResponse> {
    const response = await apiClient.post<XidianSyncResponse>('/xidian/sync/exams');
    return response.data;
  },

  async syncScores(): Promise<XidianSyncResponse> {
    const response = await apiClient.post<XidianSyncResponse>('/xidian/sync/scores');
    return response.data;
  },

  async getSnapshot(dataType: string): Promise<XidianSnapshotResponse> {
    const response = await apiClient.get<XidianSnapshotResponse>(`/xidian/snapshot/${dataType}`);
    return response.data;
  },
};

export default xidianService;
