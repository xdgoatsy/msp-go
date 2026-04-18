/**
 * useRateLimitToast - 监听限流事件并显示友好提示
 *
 * 在应用根组件中使用一次即可。当 apiClient 的 429 重试耗尽时，
 * 会通过 rateLimitEvents 发射事件，本 hook 捕获后显示 Toast。
 *
 * 设计原则：
 * - 单一职责: 只负责限流事件 → Toast 的桥接
 * - 防抖: 短时间内多个 429 只显示一次提示
 */

import { useEffect, useRef } from 'react';
import { useToast } from '@/components/ui/Toast';
import { subscribeRateLimited } from '@/libs/http/rateLimitEvents';

export function useRateLimitToast() {
  const { toast } = useToast();
  const lastToastTime = useRef(0);

  useEffect(() => {
    const unsubscribe = subscribeRateLimited((detail) => {
      // 10 秒内只显示一次，避免 Toast 轰炸
      const now = Date.now();
      if (now - lastToastTime.current < 10_000) return;
      lastToastTime.current = now;

      toast({
        type: 'warning',
        title: '操作太快啦',
        description: `请稍等 ${detail.retryAfter} 秒后再试，数据马上就来~`,
        duration: 5000,
      });
    });

    return unsubscribe;
  }, [toast]);
}
