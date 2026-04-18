import React from 'react';
import { Card, CardContent } from '../../../../components/ui/Card';
import { Button } from '../../../../components/ui/Button';
import { Check, Trash2 } from 'lucide-react';
import { cn } from '../../../../libs/utils/cn';

interface BatchSelectionBarProps {
  selectedCount: number;
  totalCount: number;
  onToggleSelectAll: () => void;
  onBatchDelete: () => void;
}

export const BatchSelectionBar = React.memo<BatchSelectionBarProps>(
  ({ selectedCount, totalCount, onToggleSelectAll, onBatchDelete }) => {
    return (
      <Card className="mb-6 border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onToggleSelectAll}
                className={cn(
                  "w-5 h-5 rounded border-2 flex items-center justify-center transition-colors",
                  selectedCount === totalCount && totalCount > 0
                    ? "bg-primary-500 border-primary-500 text-white"
                    : "border-surface-400 dark:border-surface-500"
                )}
              >
                {selectedCount === totalCount && totalCount > 0 && (
                  <Check className="w-3 h-3" />
                )}
              </button>
              <span className="text-sm text-surface-700 dark:text-surface-300">
                已选择 {selectedCount} 项
              </span>
            </div>
            <div className="flex gap-2">
              <Button
                variant="destructive"
                size="sm"
                disabled={selectedCount === 0}
                onClick={onBatchDelete}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                删除选中
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }
);

BatchSelectionBar.displayName = 'BatchSelectionBar';
