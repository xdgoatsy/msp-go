import React from 'react';
import { Card, CardContent } from '../../../../components/ui/Card';
import { Button } from '../../../../components/ui/Button';
import { CheckSquare, Copy, Trash2 } from 'lucide-react';

interface BatchActionBarProps {
  selectedCount: number;
  loading: boolean;
  onPublish: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}

export const BatchActionBar: React.FC<BatchActionBarProps> = ({
  selectedCount, loading, onPublish, onDuplicate, onDelete,
}) => (
  <Card className="mb-4">
    <CardContent className="p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckSquare className="h-4 w-4 text-primary-500" />
          <span className="text-sm text-surface-700 dark:text-surface-300">
            已选择 {selectedCount} 道题目
          </span>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onPublish} disabled={loading}>
            发布
          </Button>
          <Button variant="outline" size="sm" onClick={onDuplicate} disabled={loading}>
            <Copy className="h-4 w-4 mr-1" />
            复制
          </Button>
          <Button variant="destructive" size="sm" onClick={onDelete} disabled={loading}>
            <Trash2 className="h-4 w-4 mr-1" />
            删除
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
);
