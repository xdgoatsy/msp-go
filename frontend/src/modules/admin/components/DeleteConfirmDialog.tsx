/**
 * 删除确认弹窗组件
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface DeleteConfirmDialogProps {
  show: boolean;
  selectedCount: number;
  deleteLoading: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export const DeleteConfirmDialog: React.FC<DeleteConfirmDialogProps> = ({
  show,
  selectedCount,
  deleteLoading,
  onCancel,
  onConfirm,
}) => {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 z-10 flex items-center justify-center bg-black/30"
        >
          <motion.div
            initial={{ scale: 0.95 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0.95 }}
            className="bg-white dark:bg-surface-800 rounded-xl shadow-xl p-6 max-w-md"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                <Trash2 className="w-5 h-5 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100">
                确认删除
              </h3>
            </div>
            <p className="text-surface-600 dark:text-surface-400 mb-6">
              {selectedCount > 0
                ? `确定要删除选中的 ${selectedCount} 条日志吗？此操作不可撤销。`
                : '确定要清空所有安全日志吗？此操作不可撤销。'}
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={onCancel}>
                取消
              </Button>
              <Button
                variant="primary"
                className="bg-red-600 hover:bg-red-700"
                onClick={onConfirm}
                disabled={deleteLoading}
              >
                {deleteLoading ? '删除中...' : '确认删除'}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
