import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/libs/utils/cn';

type SectionTone = 'blue' | 'emerald' | 'fuchsia' | 'slate';

interface ChannelSectionHeaderProps {
  description: string;
  icon: LucideIcon;
  title: string;
  tone: SectionTone;
}

const toneClasses: Record<SectionTone, string> = {
  blue: 'bg-sky-50 text-sky-600 dark:bg-sky-950/60 dark:text-sky-300',
  emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-300',
  fuchsia: 'bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-950/60 dark:text-fuchsia-300',
  slate: 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-300',
};

export const ChannelSectionHeader: React.FC<ChannelSectionHeaderProps> = ({
  description,
  icon: Icon,
  title,
  tone,
}) => (
  <div className="flex items-start gap-3">
    <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-full', toneClasses[tone])}>
      <Icon className="h-5 w-5" aria-hidden="true" />
    </span>
    <div className="min-w-0 pt-0.5">
      <h3 className="text-base font-semibold text-surface-950 dark:text-white">{title}</h3>
      <p className="mt-1 text-sm leading-5 text-surface-500 dark:text-surface-400">{description}</p>
    </div>
  </div>
);
