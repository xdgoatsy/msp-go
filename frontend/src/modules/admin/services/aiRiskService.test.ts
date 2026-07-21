import { beforeEach, describe, expect, it, vi } from 'vitest';
import { aiRiskService } from './aiRiskService';
import type { AIModelReviewThresholds } from '@/modules/admin/types/aiRisk';

const modelReviewThresholds: AIModelReviewThresholds = {
  harassment: 0.98,
  'harassment/threatening': 0.9,
  hate: 0.65,
  'hate/threatening': 0.65,
  illicit: 0.95,
  'illicit/violent': 0.95,
  'self-harm': 0.65,
  'self-harm/intent': 0.85,
  'self-harm/instructions': 0.65,
  sexual: 0.65,
  'sexual/minors': 0.65,
  violence: 0.95,
  'violence/graphic': 0.95,
};

const apiClientMock = vi.hoisted(() => ({
  get: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
}));

vi.mock('@/libs/http/apiClient', () => ({
  apiClient: apiClientMock,
}));

describe('aiRiskService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads overview and settings', async () => {
    apiClientMock.get
      .mockResolvedValueOnce({ data: { total_students: 3 } })
      .mockResolvedValueOnce({ data: { daily_reply_limit: 50 } });

    await expect(aiRiskService.getOverview()).resolves.toMatchObject({ total_students: 3 });
    await expect(aiRiskService.getSettings()).resolves.toMatchObject({ daily_reply_limit: 50 });
    expect(apiClientMock.get).toHaveBeenNthCalledWith(1, '/admin/risk-control/overview');
    expect(apiClientMock.get).toHaveBeenNthCalledWith(2, '/admin/risk-control/settings');
  });

  it('updates settings and student access', async () => {
    apiClientMock.put.mockResolvedValueOnce({ data: { daily_reply_limit: 80 } });
    apiClientMock.patch.mockResolvedValueOnce({ data: { student_id: 'student-1', ai_blocked: true } });

    await aiRiskService.updateSettings({
      daily_reply_limit: 80,
      max_concurrent_requests: 3,
      blocked_keywords: ['代考'],
      model_review_enabled: true,
      model_review_thresholds: modelReviewThresholds,
    });
    await aiRiskService.updateStudentAccess('student-1', { blocked: true, reason: '违规' });

    expect(apiClientMock.put).toHaveBeenCalledWith('/admin/risk-control/settings', expect.objectContaining({ daily_reply_limit: 80 }));
    expect(apiClientMock.patch).toHaveBeenCalledWith(
      '/admin/risk-control/students/student-1/access',
      { blocked: true, reason: '违规' }
    );
  });

  it('compacts list filters', async () => {
    apiClientMock.get.mockResolvedValue({ data: { items: [], total: 0 } });

    await aiRiskService.listStudents({ page: 2, page_size: 20, search: '', status: 'all' });
    await aiRiskService.listEvents({ page: 3, event_type: 'content_blocked', search: 'alice' });

    expect(apiClientMock.get).toHaveBeenNthCalledWith(1, '/admin/risk-control/students', {
      params: { page: 2, page_size: 20 },
    });
    expect(apiClientMock.get).toHaveBeenNthCalledWith(2, '/admin/risk-control/events', {
      params: { page: 3, event_type: 'content_blocked', search: 'alice' },
    });
  });
});
