/**
 * 学习会话服务
 *
 * 提供会话创建、消息发送、历史记录等 API
 */

import { apiClient } from '@/libs/http/apiClient';
import { createSSEConnection, cancelTask, type SSEHandlers, type SSEController } from '@/libs/http/sseClient';
import { logger } from '@/libs/utils/logger';

const sessionLogger = logger.createContextLogger('SessionService');

// ========== 类型定义 ==========

/** 会话模式 */
export type SessionMode = 'study' | 'chat' | 'practice' | 'explain';

/** 消息响应 */
export interface MessageResponse {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent: string | null;
  timestamp: string;
  attachments: string[];
}

/** 创建会话响应 */
export interface CreateSessionResponse {
  session_id: string;
  user_id: string;
  topic: string | null;
  mode: string;
  status: string;
  created_at: string;
  welcome_message: MessageResponse;
}

/** 会话响应 */
export interface SessionResponse {
  session_id: string;
  user_id: string;
  topic: string | null;
  status: 'active' | 'completed' | 'paused';
  started_at: string;
  ended_at: string | null;
  message_count: number;
}

/** 会话列表响应 */
export interface SessionListResponse {
  sessions: SessionResponse[];
  total: number;
}

/** 历史消息响应 */
export interface HistoryResponse {
  messages: MessageResponse[];
  total: number;
  has_more: boolean;
}

/** 更新模式响应 */
export interface UpdateModeResponse {
  session_id: string;
  mode: string;
  topic: string | null;
}

/** 删除会话响应 */
export interface DeleteSessionResponse {
  success: boolean;
  message: string;
}

/** 批量删除会话响应 */
export interface BatchDeleteResponse {
  success: boolean;
  deleted_count: number;
  message: string;
}

// ========== 服务实现 ==========

export const sessionService = {
  /**
   * 创建会话
   *
   * @param topic - 会话主题（可选）
   * @param mode - 会话模式
   * @returns 会话信息和欢迎消息
   */
  async createSession(
    topic?: string,
    mode: SessionMode = 'chat'
  ): Promise<CreateSessionResponse> {
    sessionLogger.debug('Creating session', { topic, mode });

    const response = await apiClient.post<CreateSessionResponse>('/session/start', {
      topic,
      mode,
    });

    sessionLogger.info('Session created', { sessionId: response.data.session_id });

    return response.data;
  },

  /**
   * 流式聊天
   *
   * 建立 SSE 连接，流式接收 AI 响应
   *
   * @param sessionId - 会话 ID
   * @param message - 用户消息
   * @param handlers - 事件处理器
   * @param attachments - 附件列表（可选）
   * @returns SSE 控制器
   */
  chatStream(
    sessionId: string,
    message: string,
    handlers: SSEHandlers,
    attachments?: string[]
  ): SSEController {
    sessionLogger.debug('Starting chat stream', {
      sessionId,
      messageLength: message.length,
    });

    return createSSEConnection(
      `/api/v1/session/${sessionId}/chat`,
      {
        message,
        attachments: attachments || null,
      },
      {
        ...handlers,
        onOpen: () => {
          sessionLogger.debug('Chat stream opened', { sessionId });
          handlers.onOpen?.();
        },
        onClose: () => {
          sessionLogger.debug('Chat stream closed', { sessionId });
          handlers.onClose?.();
        },
        onError: (error) => {
          sessionLogger.error('Chat stream error', { sessionId, error });
          handlers.onError?.(error);
        },
      }
    );
  },

  /**
   * 获取会话历史
   *
   * @param sessionId - 会话 ID
   * @param limit - 返回数量限制
   * @param offset - 偏移量
   * @returns 历史消息列表
   */
  async getHistory(
    sessionId: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<HistoryResponse> {
    sessionLogger.debug('Fetching history', { sessionId, limit, offset });

    const response = await apiClient.get<HistoryResponse>(
      `/session/${sessionId}/history`,
      {
        params: { limit, offset },
      }
    );

    return response.data;
  },

  /**
   * 获取会话列表
   *
   * @param limit - 返回数量限制
   * @param offset - 偏移量
   * @returns 会话列表
   */
  async getSessions(
    limit: number = 20,
    offset: number = 0
  ): Promise<SessionListResponse> {
    sessionLogger.debug('Fetching sessions', { limit, offset });

    const response = await apiClient.get<SessionListResponse>('/session/list', {
      params: { limit, offset },
    });

    return response.data;
  },

  /**
   * 结束会话
   *
   * @param sessionId - 会话 ID
   */
  async endSession(sessionId: string): Promise<void> {
    sessionLogger.debug('Ending session', { sessionId });

    await apiClient.post(`/session/${sessionId}/end`);

    sessionLogger.info('Session ended', { sessionId });
  },

  /**
   * 取消任务
   *
   * @param taskId - 任务 ID
   * @returns 是否成功
   */
  async cancelTask(taskId: string): Promise<boolean> {
    sessionLogger.debug('Cancelling task', { taskId });

    const success = await cancelTask(taskId);

    if (success) {
      sessionLogger.info('Task cancelled', { taskId });
    } else {
      sessionLogger.warn('Failed to cancel task', { taskId });
    }

    return success;
  },

  /**
   * 更新会话模式
   *
   * @param sessionId - 会话 ID
   * @param mode - 新模式
   * @returns 更新结果
   */
  async updateSessionMode(
    sessionId: string,
    mode: SessionMode
  ): Promise<UpdateModeResponse> {
    sessionLogger.debug('Updating session mode', { sessionId, mode });

    const response = await apiClient.patch<UpdateModeResponse>(
      `/session/${sessionId}/mode`,
      { mode }
    );

    sessionLogger.info('Session mode updated', { sessionId, mode });

    return response.data;
  },

  /**
   * 删除会话
   *
   * @param sessionId - 会话 ID
   * @returns 删除结果
   */
  async deleteSession(sessionId: string): Promise<DeleteSessionResponse> {
    sessionLogger.debug('Deleting session', { sessionId });

    const response = await apiClient.delete<DeleteSessionResponse>(
      `/session/${sessionId}`
    );

    if (response.data.success) {
      sessionLogger.info('Session deleted', { sessionId });
    } else {
      sessionLogger.warn('Failed to delete session', { sessionId });
    }

    return response.data;
  },

  /**
   * 批量删除会话
   *
   * @param sessionIds - 会话 ID 列表
   * @returns 批量删除结果
   */
  async batchDeleteSessions(sessionIds: string[]): Promise<BatchDeleteResponse> {
    sessionLogger.debug('Batch deleting sessions', { count: sessionIds.length });

    const response = await apiClient.post<BatchDeleteResponse>(
      '/session/batch-delete',
      { session_ids: sessionIds }
    );

    if (response.data.success) {
      sessionLogger.info('Sessions batch deleted', { deletedCount: response.data.deleted_count });
    } else {
      sessionLogger.warn('Failed to batch delete sessions');
    }

    return response.data;
  },
};

export default sessionService;
