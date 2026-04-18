/**
 * 渠道表单底部操作按钮组件
 *
 * 包含：取消按钮、提交按钮（创建/保存）
 */

import React from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface ChannelFormActionsProps {
  isEditMode: boolean;
  isSubmitting: boolean;
  onClose: () => void;
}

export const ChannelFormActions: React.FC<ChannelFormActionsProps> = ({
  isEditMode,
  isSubmitting,
  onClose,
}) => {
  return (
    <div className="flex justify-end gap-3 px-6 py-4 border-t border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900">
      <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
        取消
      </Button>
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            提交中...
          </>
        ) : isEditMode ? (
          '保存'
        ) : (
          '创建'
        )}
      </Button>
    </div>
  );
};
