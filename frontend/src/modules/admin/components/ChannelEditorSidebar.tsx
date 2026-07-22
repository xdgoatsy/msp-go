import React from 'react';
import {
  AlertCircle,
  Boxes,
  CheckCircle2,
  Circle,
  KeyRound,
  Server,
  Settings,
} from 'lucide-react';
import { cn } from '@/libs/utils/cn';
import { ChannelProviderIcon } from './ChannelProviderIcon';

export type ChannelEditorSectionId = 'basic' | 'credentials' | 'models' | 'advanced';
export type ChannelEditorSectionStatus = 'complete' | 'configured' | 'error' | 'idle';

interface ChannelEditorSidebarProps {
  activeSection: ChannelEditorSectionId;
  completedRequiredSections: number;
  isActive: boolean;
  onNavigate: (section: ChannelEditorSectionId) => void;
  providerCode: string;
  providerLabel: string;
  statuses: Record<ChannelEditorSectionId, ChannelEditorSectionStatus>;
}

const items = [
  { id: 'basic', title: '基本信息', icon: Server },
  { id: 'credentials', title: '凭证', icon: KeyRound },
  { id: 'models', title: '模型与分组', icon: Boxes },
  { id: 'advanced', title: '高级设置', icon: Settings },
] as const;

function statusLabel(status: ChannelEditorSectionStatus): string {
  if (status === 'error') return '有错误';
  if (status === 'complete' || status === 'configured') return '已完成';
  return '未完成';
}

function StatusIcon({ status }: { status: ChannelEditorSectionStatus }) {
  if (status === 'error') return <AlertCircle className="h-4 w-4 text-red-500" aria-hidden="true" />;
  if (status === 'complete' || status === 'configured') {
    return <CheckCircle2 className="h-4 w-4 text-primary-500" aria-hidden="true" />;
  }
  return <Circle className="h-4 w-4 text-surface-400" aria-hidden="true" />;
}

export const ChannelEditorSidebar: React.FC<ChannelEditorSidebarProps> = ({
  activeSection,
  completedRequiredSections,
  isActive,
  onNavigate,
  providerCode,
  providerLabel,
  statuses,
}) => (
  <aside className="hidden self-start lg:sticky lg:top-0 lg:block">
    <div className="rounded-lg border border-surface-200 bg-surface-50/40 p-4 dark:border-surface-700 dark:bg-surface-900/30">
      <div className="flex min-w-0 items-center gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-surface-200 bg-white text-surface-800 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100">
          <ChannelProviderIcon code={providerCode} />
        </span>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium text-surface-950 dark:text-white">{providerLabel}</div>
          <div className="mt-0.5 truncate text-xs text-surface-500 dark:text-surface-400">
            {isActive ? '已启用' : '已禁用'} · {completedRequiredSections}/3
          </div>
        </div>
      </div>
    </div>

    <nav
      className="mt-4 rounded-lg border border-surface-200 bg-white p-1.5 dark:border-surface-700 dark:bg-surface-800"
      aria-label="渠道编辑步骤"
    >
      {items.map((item) => {
        const Icon = item.icon;
        const status = statuses[item.id];
        const active = activeSection === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            aria-current={active ? 'step' : undefined}
            className={cn(
              'flex w-full items-start gap-3 rounded-md px-3 py-3 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-700/70',
              active && 'bg-surface-100 dark:bg-surface-700'
            )}
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-100 text-surface-500 dark:bg-surface-700 dark:text-surface-300">
              <Icon className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-surface-900 dark:text-surface-100">
                {item.title}
              </span>
              <span className="mt-0.5 block truncate text-xs text-surface-500 dark:text-surface-400">
                {statusLabel(status)}
              </span>
            </span>
            <span className="mt-1" aria-label={statusLabel(status)}>
              <StatusIcon status={status} />
            </span>
          </button>
        );
      })}
    </nav>
  </aside>
);
