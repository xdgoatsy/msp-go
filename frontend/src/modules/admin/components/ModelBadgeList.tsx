/**
 * 已选模型标签列表组件
 *
 * 展示已选模型的 Badge 列表，支持移除单个模型
 */

import React from 'react';
import { X } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

interface ModelBadgeListProps {
  selectedModels: string[];
  onRemoveModel: (model: string) => void;
}

export const ModelBadgeList: React.FC<ModelBadgeListProps> = ({
  selectedModels,
  onRemoveModel,
}) => {
  return (
    <div className="min-h-20 p-3 border border-surface-200 dark:border-surface-700 rounded-lg bg-white dark:bg-surface-800 mb-3">
      {selectedModels.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {selectedModels.map((model) => (
            <Badge
              key={model}
              variant="default"
              className="flex items-center gap-1 px-2 py-1"
            >
              {model}
              <button
                type="button"
                onClick={() => onRemoveModel(model)}
                className="ml-1 hover:text-red-500"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        </div>
      ) : (
        <p className="text-surface-400 dark:text-surface-500 text-sm">
          请选择该渠道所支持的模型
        </p>
      )}
    </div>
  );
};
