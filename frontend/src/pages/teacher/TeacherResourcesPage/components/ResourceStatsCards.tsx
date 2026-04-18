import React from 'react';
import { Card, CardContent } from '../../../../components/ui/Card';
import { FolderOpen, Video, FileText } from 'lucide-react';
import type { FilterType } from '../types';

interface ResourceStatsCardsProps {
  stats: {
    total: number;
    videos: number;
    documents: number;
    favorites: number;
  };
  loading: boolean;
  onTypeSelect: (type: FilterType) => void;
}

export const ResourceStatsCards = React.memo<ResourceStatsCardsProps>(
  ({ stats, loading, onTypeSelect }) => {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <Card
          className="cursor-pointer hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors"
          onClick={() => onTypeSelect('all')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-surface-100 dark:bg-surface-800 rounded-lg">
                <FolderOpen className="w-5 h-5 text-surface-600 dark:text-surface-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                  {loading ? '-' : stats.total}
                </div>
                <div className="text-sm text-surface-500">全部资源</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
          onClick={() => onTypeSelect('video')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-50 dark:bg-primary-900/30 rounded-lg">
                <Video className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                  {loading ? '-' : stats.videos}
                </div>
                <div className="text-sm text-surface-500">教学视频</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer hover:border-secondary-300 dark:hover:border-secondary-700 transition-colors"
          onClick={() => onTypeSelect('document')}
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-secondary-50 dark:bg-secondary-900/30 rounded-lg">
                <FileText className="w-5 h-5 text-secondary-600 dark:text-secondary-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                  {loading ? '-' : stats.documents}
                </div>
                <div className="text-sm text-surface-500">学习文档</div>
              </div>
            </div>
          </CardContent>
        </Card>

      </div>
    );
  }
);

ResourceStatsCards.displayName = 'ResourceStatsCards';
