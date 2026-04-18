/**
 * 渠道模型选择器组件
 *
 * 包含：已选模型列表、获取模型按钮、可用模型列表、自定义模型输入
 */

import React from 'react';
import { Code2, Plus, Trash2, RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/libs/utils/cn';
import { ModelBadgeList } from './ModelBadgeList';

interface ChannelModelSelectorProps {
  selectedModels: string[];
  availableModels: string[];
  customModel: string;
  isFetchingModels: boolean;
  canFetchModels: boolean;
  onFetchModels: () => void;
  onClearModels: () => void;
  onAddModel: (model: string) => void;
  onAddAllModels: () => void;
  onRemoveModel: (model: string) => void;
  onCustomModelChange: (value: string) => void;
  onAddCustomModel: () => void;
}

export const ChannelModelSelector: React.FC<ChannelModelSelectorProps> = ({
  selectedModels,
  availableModels,
  customModel,
  isFetchingModels,
  canFetchModels,
  onFetchModels,
  onClearModels,
  onAddModel,
  onAddAllModels,
  onRemoveModel,
  onCustomModelChange,
  onAddCustomModel,
}) => {
  return (
    <div className="bg-surface-50 dark:bg-surface-900 rounded-xl p-4 space-y-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
          <Code2 className="w-4 h-4 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h3 className="font-medium text-surface-900 dark:text-surface-100">模型配置</h3>
          <p className="text-xs text-surface-500 dark:text-surface-400">模型选择和映射设置</p>
        </div>
      </div>

      {/* 模型选择 */}
      <div>
        <label className="block text-sm font-medium text-surface-900 dark:text-surface-100 mb-2">
          模型 <span className="text-red-500">*</span>
        </label>

        {/* 已选模型标签 */}
        <ModelBadgeList selectedModels={selectedModels} onRemoveModel={onRemoveModel} />

        {/* 快捷按钮 */}
        <div className="flex flex-wrap gap-2 mb-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onFetchModels}
            disabled={isFetchingModels || !canFetchModels}
            title={!canFetchModels ? '请先填写 API 地址和密钥' : ''}
          >
            {isFetchingModels ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-1" />
            )}
            获取模型
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onClearModels}
            className="text-red-600 dark:text-red-400 border-red-300 dark:border-red-700"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            清除所有模型
          </Button>
        </div>

        {/* 可用模型列表（从 API 获取） */}
        {availableModels.length > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-surface-900 dark:text-surface-100">
                可用模型 ({availableModels.length})
              </label>
              <Button type="button" variant="ghost" size="sm" onClick={onAddAllModels}>
                全部添加
              </Button>
            </div>
            <div className="max-h-[200px] overflow-y-auto p-3 border border-surface-200 dark:border-surface-700 rounded-lg bg-white dark:bg-surface-800">
              <div className="flex flex-wrap gap-2">
                {availableModels.map((model) => {
                  const isSelected = selectedModels.includes(model);
                  return (
                    <Badge
                      key={model}
                      variant={isSelected ? 'default' : 'outline'}
                      className={cn(
                        'cursor-pointer transition-colors',
                        isSelected
                          ? 'opacity-50 cursor-not-allowed'
                          : 'hover:bg-primary-100 dark:hover:bg-primary-900/30'
                      )}
                      onClick={() => !isSelected && onAddModel(model)}
                    >
                      {model}
                      {!isSelected && <Plus className="w-3 h-3 ml-1" />}
                    </Badge>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* 自定义模型 */}
        <div>
          <label className="block text-sm font-medium text-surface-900 dark:text-surface-100 mb-2">
            自定义模型名称
          </label>
          <div className="flex gap-2">
            <Input
              value={customModel}
              onChange={(e) => onCustomModelChange(e.target.value)}
              placeholder="输入自定义模型名称"
              className="flex-1"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  onAddCustomModel();
                }
              }}
            />
            <Button
              type="button"
              variant="outline"
              onClick={onAddCustomModel}
              disabled={!customModel.trim()}
            >
              <Plus className="w-4 h-4 mr-1" />
              填入
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
