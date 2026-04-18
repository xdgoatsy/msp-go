import React from 'react';
import { Card, CardContent } from '../../../../components/ui/Card';
import { Input } from '../../../../components/ui/Input';
import { Search, Grid, List } from 'lucide-react';
import { cn } from '../../../../libs/utils/cn';
import type { FilterType, ViewMode } from '../types';

interface ResourceFiltersProps {
  searchTerm: string;
  selectedType: FilterType;
  viewMode: ViewMode;
  onSearchChange: (term: string) => void;
  onTypeChange: (type: FilterType) => void;
  onViewModeChange: (mode: ViewMode) => void;
}

export const ResourceFilters = React.memo<ResourceFiltersProps>(
  ({ searchTerm, selectedType, viewMode, onSearchChange, onTypeChange, onViewModeChange }) => {
    return (
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
              <Input
                placeholder="搜索资源..."
                value={searchTerm}
                onChange={(e) => onSearchChange(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={selectedType}
                onChange={(e) => onTypeChange(e.target.value as FilterType)}
                className="px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="all">全部类型</option>
                <option value="video">视频</option>
                <option value="document">文档</option>
              </select>
              <div className="flex border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
                <button
                  onClick={() => onViewModeChange('grid')}
                  className={cn(
                    "p-2 transition-colors",
                    viewMode === 'grid'
                      ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-400"
                      : "text-surface-400 hover:text-surface-600"
                  )}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onViewModeChange('list')}
                  className={cn(
                    "p-2 transition-colors",
                    viewMode === 'list'
                      ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-400"
                      : "text-surface-400 hover:text-surface-600"
                  )}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }
);

ResourceFilters.displayName = 'ResourceFilters';
