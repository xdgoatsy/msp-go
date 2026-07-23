/**
 * 渠道表单底部操作按钮组件
 *
 * 包含：取消按钮、提交按钮（创建/保存）
 */

import React from 'react';
import { Loader2, Save } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface ChannelFormActionsProps {
  isEditMode: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  submitLabel?: string;
}

export const ChannelFormActions: React.FC<ChannelFormActionsProps> = ({
  isEditMode,
  isSubmitting,
  onClose,
  submitLabel,
}) => {
  return (
    <div className="flex items-center justify-end gap-3 border-t border-surface-200 bg-white/95 px-5 py-4 backdrop-blur sm:px-7 dark:border-surface-700 dark:bg-surface-900/95">
      <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting} className="min-w-20">
        取消
      </Button>
      <Button type="submit" disabled={isSubmitting} className="min-w-28">
        {isSubmitting ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            提交中...
          </>
        ) : (
          <>
            <Save className="mr-2 h-4 w-4" aria-hidden="true" />
            {submitLabel ?? (isEditMode ? '保存更改' : '创建渠道')}
          </>
        )}
      </Button>
    </div>
  );
};
