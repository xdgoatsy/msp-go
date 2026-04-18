/**
 * SSE 客户端封装
 *
 * 提供 POST 请求的 SSE 流式连接支持
 */

import { logger } from '../utils/logger';

const sseLogger = logger.createContextLogger('SSE');

/**
 * SSE 事件处理器
 */
export interface SSEHandlers {
  /** 收到内容块 */
  onChunk?: (content: string, agent: string | null, messageId: string) => void;
  /** 流式响应完成 */
  onDone?: (messageId: string, agent: string | null) => void;
  /** 发生错误 */
  onError?: (error: { code: string; message: string }) => void;
  /** 任务被取消 */
  onCancelled?: (messageId: string) => void;
  /** 收到任务信息 */
  onTaskInfo?: (taskId: string) => void;
  /** 连接打开 */
  onOpen?: () => void;
  /** 连接关闭 */
  onClose?: () => void;
}

/**
 * SSE 连接控制器
 */
export interface SSEController {
  /** 关闭连接 */
  close: () => void;
  /** 获取任务 ID */
  getTaskId: () => string | null;
}

/**
 * 创建 SSE 连接（使用 fetch + ReadableStream）
 *
 * 由于标准 EventSource 不支持 POST 请求和自定义 headers，
 * 这里使用 fetch API 实现 SSE 客户端
 *
 * @param url - SSE 端点 URL
 * @param body - 请求体
 * @param handlers - 事件处理器
 * @returns SSE 控制器
 */
export function createSSEConnection(
  url: string,
  body: object,
  handlers: SSEHandlers
): SSEController {
  let taskId: string | null = null;
  let abortController: AbortController | null = new AbortController();
  let isClosed = false;

  const close = () => {
    if (isClosed) return;
    isClosed = true;
    abortController?.abort();
    abortController = null;
    handlers.onClose?.();
    sseLogger.debug('SSE connection closed');
  };

  // 启动连接
  (async () => {
    try {
      const token = localStorage.getItem('auth_token');

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: abortController?.signal,
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      handlers.onOpen?.();
      sseLogger.debug('SSE connection opened', { url });

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      // 将 currentEvent 和 currentData 移到 while 循环外部
      // 以正确处理跨 chunk 的 SSE 事件
      let currentEvent = '';
      let currentData = '';

      while (!isClosed) {
        const { done, value } = await reader.read();

        if (done) {
          sseLogger.debug('SSE stream ended');
          // 处理最后可能未完成的事件
          if (currentData) {
            processEvent(currentEvent, currentData, handlers, (id) => {
              taskId = id;
            });
          }
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // 解析 SSE 事件 - 统一处理 \r\n 和 \n 换行符
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留不完整的行

        for (const rawLine of lines) {
          // 移除行末的 \r（处理 Windows 风格换行符 \r\n）
          const line = rawLine.replace(/\r$/, '');

          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            currentData = line.slice(5).trim();
          } else if (line === '' && currentData) {
            // 空行表示事件结束
            processEvent(currentEvent, currentData, handlers, (id) => {
              taskId = id;
            });
            currentEvent = '';
            currentData = '';
          }
        }
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        sseLogger.debug('SSE connection aborted');
        return;
      }

      sseLogger.error('SSE connection error', error);
      handlers.onError?.({
        code: 'CONNECTION_ERROR',
        message: (error as Error).message || '连接失败',
      });
    } finally {
      close();
    }
  })();

  return {
    close,
    getTaskId: () => taskId,
  };
}

/**
 * 处理 SSE 事件
 */
function processEvent(
  event: string,
  data: string,
  handlers: SSEHandlers,
  setTaskId: (id: string) => void
): void {
  try {
    const parsed = JSON.parse(data);

    switch (event || parsed.type) {
      case 'task_info':
        if (parsed.task_id) {
          setTaskId(parsed.task_id);
          handlers.onTaskInfo?.(parsed.task_id);
        }
        break;

      case 'message':
        if (parsed.type === 'chunk' || parsed.type === 'stream') {
          handlers.onChunk?.(
            parsed.content || '',
            parsed.agent || null,
            parsed.message_id || ''
          );
        } else if (parsed.type === 'done') {
          handlers.onDone?.(parsed.message_id || '', parsed.agent || null);
        }
        break;

      case 'error':
        handlers.onError?.({
          code: parsed.code || 'UNKNOWN_ERROR',
          message: parsed.message || '未知错误',
        });
        break;

      case 'cancelled':
        handlers.onCancelled?.(parsed.message_id || parsed.task_id || '');
        break;

      default:
        // 处理没有 event 字段的消息
        if (parsed.type === 'chunk' || parsed.type === 'stream') {
          handlers.onChunk?.(
            parsed.content || '',
            parsed.agent || null,
            parsed.message_id || ''
          );
        } else if (parsed.type === 'done') {
          handlers.onDone?.(parsed.message_id || '', parsed.agent || null);
        } else if (parsed.type === 'error') {
          handlers.onError?.({
            code: parsed.code || 'UNKNOWN_ERROR',
            message: parsed.message || '未知错误',
          });
        }
    }
  } catch (e) {
    sseLogger.warn('Failed to parse SSE event', { event, data, error: e });
  }
}

/**
 * 取消任务
 *
 * @param taskId - 任务 ID
 * @returns 是否成功
 */
export async function cancelTask(taskId: string): Promise<boolean> {
  try {
    const token = localStorage.getItem('auth_token');

    const response = await fetch(`/api/v1/session/task/${taskId}/cancel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      credentials: 'include',
    });

    if (!response.ok) {
      return false;
    }

    const result = await response.json();
    return result.success === true;
  } catch (error) {
    sseLogger.error('Failed to cancel task', { taskId, error });
    return false;
  }
}
