import { motion, useReducedMotion } from 'framer-motion';
import {
  Activity,
  BookOpenCheck,
  Clock3,
  Flame,
  Target,
  Users,
  ClipboardCheck,
} from 'lucide-react';
import type { HomeStat, HomeStatTone } from './types';

interface HomeStatsStripProps {
  stats: HomeStat[];
  loading: boolean;
}

const toneClasses: Record<HomeStatTone, { icon: string }> = {
  blue: {
    icon: 'text-primary-600 dark:text-primary-300',
  },
  violet: {
    icon: 'text-secondary-600 dark:text-secondary-300',
  },
  emerald: {
    icon: 'text-emerald-600 dark:text-emerald-300',
  },
  coral: {
    icon: 'text-rose-500 dark:text-rose-300',
  },
};

const statIcons = {
  'study-time': Clock3,
  accuracy: Target,
  streak: Flame,
  mastered: BookOpenCheck,
  students: Users,
  active: Activity,
  completion: Target,
  grading: ClipboardCheck,
} as const;

export function HomeStatsStrip({ stats, loading }: HomeStatsStripProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <section aria-label="个人概览" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
      <div className="grid overflow-hidden rounded-lg border border-surface-200 bg-white shadow-sm sm:grid-cols-2 lg:grid-cols-4 dark:border-surface-800 dark:bg-surface-900">
        {stats.map((stat, index) => {
          const Icon = statIcons[stat.key as keyof typeof statIcons] ?? Activity;
          const tone = toneClasses[stat.tone];
          return (
            <motion.div
              key={stat.key}
              initial={shouldReduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: shouldReduceMotion ? 0 : 0.32, delay: shouldReduceMotion ? 0 : index * 0.05 }}
              className="flex min-h-24 items-center gap-4 border-b border-surface-100 px-5 py-4 sm:nth-[2n]:border-l lg:border-b-0 lg:border-l lg:first:border-l-0 dark:border-surface-800"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center">
                <Icon className={`h-8 w-8 ${tone.icon}`} aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-sm text-surface-500 dark:text-surface-400">{stat.label}</p>
                {loading ? (
                  <div className="mt-2 h-7 w-24 animate-pulse rounded bg-surface-100 motion-reduce:animate-none dark:bg-surface-800" />
                ) : (
                  <motion.p
                    key={stat.value}
                    initial={shouldReduceMotion ? false : { opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-1 truncate text-2xl font-semibold text-surface-950 dark:text-white"
                  >
                    {stat.value}
                  </motion.p>
                )}
                {stat.detail && !loading ? (
                  <p className="mt-1 truncate text-xs text-surface-500 dark:text-surface-400">{stat.detail}</p>
                ) : null}
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
