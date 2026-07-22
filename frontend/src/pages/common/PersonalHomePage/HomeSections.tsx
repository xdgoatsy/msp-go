import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  CirclePause,
  Clock3,
  GraduationCap,
  MessageCircle,
  School,
  Users,
} from 'lucide-react';
import type {
  HomeActionItem,
  HomeAffiliation,
  HomeRecentItem,
  HomeRole,
  HomeStatTone,
} from './types';

interface HomeSectionsProps {
  role: HomeRole;
  actions: HomeActionItem[];
  recentItems: HomeRecentItem[];
  affiliation: HomeAffiliation;
  recentUnavailable: boolean;
  loading: boolean;
}

const toneClasses: Record<HomeStatTone, { text: string; surface: string; bar: string }> = {
  blue: {
    text: 'text-primary-600 dark:text-primary-300',
    surface: 'bg-primary-50 dark:bg-primary-950/60',
    bar: 'bg-primary-500',
  },
  violet: {
    text: 'text-secondary-600 dark:text-secondary-300',
    surface: 'bg-secondary-50 dark:bg-secondary-950/60',
    bar: 'bg-secondary-500',
  },
  emerald: {
    text: 'text-emerald-600 dark:text-emerald-300',
    surface: 'bg-emerald-50 dark:bg-emerald-950/50',
    bar: 'bg-emerald-500',
  },
  coral: {
    text: 'text-rose-500 dark:text-rose-300',
    surface: 'bg-rose-50 dark:bg-rose-950/50',
    bar: 'bg-rose-500',
  },
};

function SectionHeading({ children, icon: Icon }: { children: React.ReactNode; icon: typeof BookOpen }) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="h-5 w-5 text-primary-600 dark:text-primary-300" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-surface-950 dark:text-white">{children}</h2>
    </div>
  );
}

function LoadingRows({ count = 3 }: { count?: number }) {
  return (
    <div className="divide-y divide-surface-100 dark:divide-surface-800">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="flex min-h-24 items-center gap-4 py-4">
          <div className="h-11 w-11 shrink-0 animate-pulse rounded-lg bg-surface-100 motion-reduce:animate-none dark:bg-surface-800" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-2/5 animate-pulse rounded bg-surface-100 motion-reduce:animate-none dark:bg-surface-800" />
            <div className="h-3 w-3/4 animate-pulse rounded bg-surface-100 motion-reduce:animate-none dark:bg-surface-800" />
          </div>
        </div>
      ))}
    </div>
  );
}

function ActionList({ role, items, loading }: { role: HomeRole; items: HomeActionItem[]; loading: boolean }) {
  const shouldReduceMotion = useReducedMotion();
  const title = role === 'teacher' ? '今天的教学重点' : '今天可以继续';

  return (
    <section className="rounded-lg border border-surface-200 bg-white px-5 py-5 shadow-sm sm:px-7 dark:border-surface-800 dark:bg-surface-900">
      <SectionHeading icon={role === 'teacher' ? GraduationCap : BookOpen}>{title}</SectionHeading>
      <p className="mt-2 text-sm leading-6 text-surface-500 dark:text-surface-400">
        {role === 'teacher'
          ? '从掌握度较低的知识点开始安排本周教学。'
          : '从薄弱知识点或常用学习入口开始，不必先加入班级。'}
      </p>

      <div className="mt-4">
        {loading ? <LoadingRows /> : (
          <div className="divide-y divide-surface-100 dark:divide-surface-800">
            {items.map((item, index) => {
              const tone = toneClasses[item.tone];
              return (
                <motion.div
                  key={item.id}
                  initial={shouldReduceMotion ? false : { opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: shouldReduceMotion ? 0 : 0.3, delay: shouldReduceMotion ? 0 : index * 0.06 }}
                >
                  <Link
                    to={item.href}
                    className="group grid min-h-24 grid-cols-[auto_1fr_auto] items-center gap-4 py-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-surface-900"
                  >
                    <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${tone.surface} ${tone.text}`}>
                      <span className="text-sm font-bold">{index + 1}</span>
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                        <h3 className="truncate text-base font-semibold text-surface-900 group-hover:text-primary-700 dark:text-surface-100 dark:group-hover:text-primary-300">
                          {item.title}
                        </h3>
                        {item.meta ? <span className="text-xs text-surface-500 dark:text-surface-400">{item.meta}</span> : null}
                      </div>
                      <p className="mt-1 line-clamp-2 text-sm leading-5 text-surface-500 dark:text-surface-400">
                        {item.description}
                      </p>
                      {item.progress != null ? (
                        <div className="mt-3 h-1.5 max-w-sm overflow-hidden rounded-full bg-surface-100 dark:bg-surface-800">
                          <motion.div
                            initial={shouldReduceMotion ? false : { width: 0 }}
                            animate={{ width: `${item.progress}%` }}
                            transition={{ duration: shouldReduceMotion ? 0 : 0.65, delay: shouldReduceMotion ? 0 : 0.12 + index * 0.08 }}
                            className={`h-full rounded-full ${tone.bar}`}
                          />
                        </div>
                      ) : null}
                    </div>
                    <ArrowRight className="h-4 w-4 text-surface-300 transition-transform group-hover:translate-x-0.5 group-hover:text-primary-600 motion-reduce:transform-none dark:text-surface-600 dark:group-hover:text-primary-300" aria-hidden="true" />
                  </Link>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function RecentItems({
  role,
  items,
  loading,
  unavailable,
}: {
  role: HomeRole;
  items: HomeRecentItem[];
  loading: boolean;
  unavailable: boolean;
}) {
  const shouldReduceMotion = useReducedMotion();
  const emptyHref = role === 'teacher' ? '/teacher/classes' : '/session/new';
  const emptyLabel = role === 'teacher' ? '管理班级' : '开始 AI 辅导';
  const title = role === 'teacher' ? '最近班级' : '最近学习';

  const statusIcon = (status: HomeRecentItem['status']) => {
    if (status === 'completed') return CheckCircle2;
    if (status === 'paused') return CirclePause;
    if (status === 'active') return MessageCircle;
    return Users;
  };

  return (
    <section className="rounded-lg border border-surface-200 bg-white px-5 py-5 shadow-sm dark:border-surface-800 dark:bg-surface-900">
      <div className="flex items-center justify-between gap-4">
        <SectionHeading icon={Clock3}>{title}</SectionHeading>
        <Link
          to={role === 'teacher' ? '/teacher/classes' : '/session/new'}
          className="text-sm font-medium text-primary-700 hover:text-primary-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:text-primary-300 dark:hover:text-primary-200"
        >
          {role === 'teacher' ? '查看全部' : '新建会话'}
        </Link>
      </div>

      <div className="mt-3">
        {loading ? <LoadingRows /> : unavailable ? (
          <div className="py-8 text-center">
            <p className="text-sm text-surface-500 dark:text-surface-400">
              {role === 'teacher' ? '班级列表暂时无法加载' : '学习记录暂时无法加载'}
            </p>
            <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">其他常用入口仍可正常使用</p>
          </div>
        ) : items.length > 0 ? (
          <div className="divide-y divide-surface-100 dark:divide-surface-800">
            {items.map((item, index) => {
              const StatusIcon = statusIcon(item.status);
              return (
                <motion.div
                  key={item.id}
                  initial={shouldReduceMotion ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: shouldReduceMotion ? 0 : 0.28, delay: shouldReduceMotion ? 0 : index * 0.05 }}
                >
                  <Link
                    to={item.href}
                    className="group grid grid-cols-[auto_1fr_auto] items-center gap-3 py-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                  >
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-50 text-surface-500 group-hover:bg-primary-50 group-hover:text-primary-600 dark:bg-surface-800 dark:text-surface-400 dark:group-hover:bg-primary-950/60 dark:group-hover:text-primary-300">
                      <StatusIcon className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold text-surface-900 group-hover:text-primary-700 dark:text-surface-100 dark:group-hover:text-primary-300">
                        {item.title}
                      </h3>
                      <p className="mt-1 truncate text-xs text-surface-500 dark:text-surface-400">{item.description}</p>
                    </div>
                    <time className="whitespace-nowrap text-xs text-surface-500 dark:text-surface-400">{item.timestamp}</time>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        ) : (
          <div className="py-8 text-center">
            <p className="text-sm text-surface-500 dark:text-surface-400">暂时还没有可显示的记录</p>
            <Link
              to={emptyHref}
              className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary-700 hover:text-primary-800 dark:text-primary-300 dark:hover:text-primary-200"
            >
              {emptyLabel}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}

function AffiliationPanel({ role, affiliation, loading }: { role: HomeRole; affiliation: HomeAffiliation; loading: boolean }) {
  return (
    <section className="rounded-lg border border-surface-200 bg-white px-5 py-5 shadow-sm dark:border-surface-800 dark:bg-surface-900">
      <SectionHeading icon={School}>{role === 'teacher' ? '我的教学' : '我的班级'}</SectionHeading>
      {loading ? (
        <div className="mt-5 flex items-center gap-4">
          <div className="h-12 w-12 animate-pulse rounded-lg bg-surface-100 motion-reduce:animate-none dark:bg-surface-800" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-1/2 animate-pulse rounded bg-surface-100 motion-reduce:animate-none dark:bg-surface-800" />
            <div className="h-3 w-3/4 animate-pulse rounded bg-surface-100 motion-reduce:animate-none dark:bg-surface-800" />
          </div>
        </div>
      ) : (
        <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg ${affiliation.empty || affiliation.unavailable ? 'bg-surface-100 text-surface-500 dark:bg-surface-800 dark:text-surface-400' : 'bg-secondary-50 text-secondary-600 dark:bg-secondary-950/60 dark:text-secondary-300'}`}>
            {role === 'teacher' ? <Users className="h-6 w-6" aria-hidden="true" /> : <GraduationCap className="h-6 w-6" aria-hidden="true" />}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-base font-semibold text-surface-950 dark:text-white">{affiliation.title}</h3>
            <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">{affiliation.subtitle}</p>
            {affiliation.detail ? <p className="mt-1 text-xs text-surface-500 dark:text-surface-400">{affiliation.detail}</p> : null}
          </div>
          <Link
            to={affiliation.href}
            className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg border border-primary-200 px-4 text-sm font-semibold text-primary-700 transition-colors hover:border-primary-300 hover:bg-primary-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:border-primary-800 dark:text-primary-300 dark:hover:border-primary-700 dark:hover:bg-primary-950/50"
          >
            {affiliation.actionLabel}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      )}
    </section>
  );
}

export function HomeSections({
  role,
  actions,
  recentItems,
  affiliation,
  recentUnavailable,
  loading,
}: HomeSectionsProps) {
  return (
    <div className="mx-auto grid max-w-7xl gap-4 px-4 pb-8 pt-4 sm:px-6 lg:grid-cols-[1.02fr_0.98fr] lg:px-8">
      <ActionList role={role} items={actions} loading={loading} />
      <div className="space-y-4">
        <RecentItems role={role} items={recentItems} loading={loading} unavailable={recentUnavailable} />
        <AffiliationPanel role={role} affiliation={affiliation} loading={loading} />
      </div>
    </div>
  );
}
