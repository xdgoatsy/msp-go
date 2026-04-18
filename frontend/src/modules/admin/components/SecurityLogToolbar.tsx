/**
 * 安全日志工具栏组件（筛选切换、刷新、删除、导出）
 */

import React from 'react';
import { Filter, ChevronDown, RefreshCw, Trash2, Download } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface SecurityLogToolbarProps {
  showFilters: boolean;
  loading: 'idle' | 'loading' | 'succeeded' | 'failed';
  exportLoading: boolean;
  total: number;
  selectedIds: string[];
  exportFormat: 'json' | 'csv';
  onToggleFilters: () => void;
  onRefresh: () => void;
  onShowDeleteConfirm: () => void;
  onExportFormatChange: (format: 'json' | 'csv') => void;
  onExport: () => void;
}

export const SecurityLogToolbar: React.FC<SecurityLogToolbarProps> = ({
  showFilters,
  loading,
  exportLoading,
  total,
  selectedIds,
  exportFormat,
  onToggleFilters,
  onRefresh,
  onShowDeleteConfirm,
  onExportFormatChange,
  onExport,
}) => {
  return (
    <div className="flex items-center justify-between px-6 py-3 border-b border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/50">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onToggleFilters}
        >
          <Filter className="w-4 h-4 mr-1" />
          筛选
          <ChevronDown className={`w-4 h-4 ml-1 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={loading === 'loading'}
        >
          <RefreshCw className={`w-4 h-4 mr-1 ${loading === 'loading' ? 'animate-spin' : ''}`} />
          刷新
        </Button>

        {selectedIds.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={onShowDeleteConfirm}
            className="text-red-600 border-red-200 hover:bg-red-50"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            删除 ({selectedIds.length})
          </Button>
        )}
      </div>

      <div className="flex items-center gap-2">
        <select
          value={exportFormat}
          onChange={(e) => onExportFormatChange(e.target.value as 'json' | 'csv')}
          className="px-2 py-1.5 text-sm border border-surface-200 dark:border-surface-600 rounded-lg bg-white dark:bg-surface-700"
        >
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
        </select>
        <Button
          variant="outline"
          size="sm"
          onClick={onExport}
          disabled={exportLoading || total === 0}
        >
          <Download className="w-4 h-4 mr-1" />
          导出
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={onShowDeleteConfirm}
          className="text-red-600 border-red-200 hover:bg-red-50"
        >
          <Trash2 className="w-4 h-4 mr-1" />
          清空
        </Button>
      </div>
    </div>
  );
};
