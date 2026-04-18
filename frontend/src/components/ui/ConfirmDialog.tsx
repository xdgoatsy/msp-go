import React from 'react';
import { Modal } from './Modal';
import { Button } from './Button';
import { Loader2, Trash2 } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  loading?: boolean;
  title: string;
  message: React.ReactNode;
  /** 批量操作时显示的数量 */
  count?: number;
  /** 确认按钮文字，默认"删除" */
  confirmText?: string;
  /** 确认按钮变体，默认 destructive */
  confirmVariant?: 'destructive' | 'primary' | 'outline';
  /** 是否显示删除图标，默认 true */
  showIcon?: boolean;
}

export const ConfirmDialog = React.memo<ConfirmDialogProps>(
  ({ isOpen, onClose, onConfirm, loading = false, title, message, count, confirmText, confirmVariant = 'destructive', showIcon = true }) => {
    const defaultConfirmText = count ? `删除 ${count} 项` : '删除';
    const finalConfirmText = confirmText ?? defaultConfirmText;

    return (
      <Modal isOpen={isOpen} onClose={onClose} title={title}>
        <div className="space-y-4">
          <div className="text-surface-600 dark:text-surface-400">{message}</div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose} disabled={loading}>
              取消
            </Button>
            <Button variant={confirmVariant} onClick={onConfirm} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  处理中...
                </>
              ) : (
                <>
                  {showIcon && <Trash2 className="w-4 h-4 mr-2" />}
                  {finalConfirmText}
                </>
              )}
            </Button>
          </div>
        </div>
      </Modal>
    );
  }
);

ConfirmDialog.displayName = 'ConfirmDialog';
