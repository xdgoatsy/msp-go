import { useCallback, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { useAppSelector } from '@/store';
import { selectCurrentUser } from '@/modules/auth/store/authSlice';
import { HomeHero } from './HomeHero';
import { HomeStatsStrip } from './HomeStatsStrip';
import { HomeSections } from './HomeSections';
import { loadStudentHomeData, loadTeacherHomeData } from './homeData';
import type { PersonalHomeData, HomeRole } from './types';

interface PersonalHomeViewProps {
  role: HomeRole;
  displayName: string;
  data: PersonalHomeData;
  loading: boolean;
  onRetry: () => void;
}

const loadingData: Record<HomeRole, PersonalHomeData> = {
  student: {
    role: 'student',
    primaryHref: '/exercise',
    primaryLabel: '开始学习',
    primaryContext: '正在整理你的学习进度',
    stats: [
      { key: 'study-time', label: '累计学习', value: '—', tone: 'blue' },
      { key: 'accuracy', label: '正确率', value: '—', tone: 'violet' },
      { key: 'streak', label: '连续学习', value: '—', tone: 'emerald' },
      { key: 'mastered', label: '已掌握', value: '—', tone: 'coral' },
    ],
    actions: [],
    recentItems: [],
    affiliation: {
      title: '班级信息加载中',
      subtitle: '稍等片刻',
      href: '/my-class',
      actionLabel: '我的班级',
      empty: true,
    },
    failedSections: [],
  },
  teacher: {
    role: 'teacher',
    primaryHref: '/teacher/dashboard',
    primaryLabel: '进入教学概览',
    primaryContext: '正在整理今天的教学数据',
    stats: [
      { key: 'students', label: '学生总数', value: '—', tone: 'blue' },
      { key: 'active', label: '今日活跃', value: '—', tone: 'violet' },
      { key: 'completion', label: '平均完成率', value: '—', tone: 'emerald' },
      { key: 'grading', label: '待批改', value: '—', tone: 'coral' },
    ],
    actions: [],
    recentItems: [],
    affiliation: {
      title: '教学信息加载中',
      subtitle: '稍等片刻',
      href: '/teacher/classes',
      actionLabel: '班级管理',
      empty: true,
    },
    failedSections: [],
  },
};

const unexpectedFailureLabel = '主页数据';

function markHomeUnavailable(data: PersonalHomeData): PersonalHomeData {
  return {
    ...data,
    primaryContext: data.role === 'teacher'
      ? '主页数据暂时无法加载，仍可进入教学概览'
      : '主页数据暂时无法加载，仍可开始学习',
    affiliation: {
      ...data.affiliation,
      title: data.role === 'teacher' ? '教学信息暂不可用' : '班级信息暂不可用',
      subtitle: '常用入口仍可正常使用',
      detail: '可以稍后重新加载',
      empty: false,
      unavailable: true,
    },
    failedSections: data.failedSections.includes(unexpectedFailureLabel)
      ? data.failedSections
      : [...data.failedSections, unexpectedFailureLabel],
  };
}

export function PersonalHomeView({
  role,
  displayName,
  data,
  loading,
  onRetry,
}: PersonalHomeViewProps) {
  return (
    <MainLayout showFooter={false} className="bg-white dark:bg-surface-950">
      <div className="min-h-[calc(100vh-4rem)] bg-white dark:bg-surface-950">
        <HomeHero
          role={role}
          name={displayName}
          primaryHref={data.primaryHref}
          primaryLabel={data.primaryLabel}
          primaryContext={data.primaryContext}
        />

        <div className="relative z-10 -mt-px pt-5">
          <HomeStatsStrip stats={data.stats} loading={loading} />
        </div>

        {data.failedSections.length > 0 && !loading ? (
          <div className="mx-auto mt-5 max-w-7xl px-4 sm:px-6 lg:px-8">
            <div
              role="status"
              aria-live="polite"
              className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 sm:flex-row sm:items-center sm:justify-between dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200"
            >
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>部分数据暂时未能加载，常用入口仍可正常使用。</span>
              </div>
              <button
                type="button"
                onClick={onRetry}
                className="inline-flex h-9 items-center justify-center gap-2 rounded-md px-3 font-medium transition-colors hover:bg-amber-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 dark:hover:bg-amber-900/40"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                重新加载
              </button>
            </div>
          </div>
        ) : null}

        <HomeSections
          role={role}
          actions={data.actions}
          recentItems={data.recentItems}
          affiliation={data.affiliation}
          recentUnavailable={data.failedSections.includes(role === 'teacher' ? '班级信息' : '学习记录') || data.failedSections.includes(unexpectedFailureLabel)}
          loading={loading}
        />
      </div>
    </MainLayout>
  );
}

export function PersonalHomePage() {
  const user = useAppSelector(selectCurrentUser);
  const role: HomeRole = user?.role === 'teacher' ? 'teacher' : 'student';
  const [data, setData] = useState<PersonalHomeData>(() => loadingData[role]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const nextData = role === 'teacher'
        ? await loadTeacherHomeData()
        : await loadStudentHomeData();
      setData(nextData);
    } catch {
      setData((currentData) => markHomeUnavailable(currentData));
    } finally {
      setLoading(false);
    }
  }, [role]);

  useEffect(() => {
    let active = true;
    if (user?.role === 'admin') return undefined;

    setData(loadingData[role]);
    setLoading(true);

    const run = async () => {
      try {
        const nextData = role === 'teacher'
          ? await loadTeacherHomeData()
          : await loadStudentHomeData();
        if (active) setData(nextData);
      } catch {
        if (active) setData((currentData) => markHomeUnavailable(currentData));
      } finally {
        if (active) setLoading(false);
      }
    };

    void run();
    return () => {
      active = false;
    };
  }, [role, user?.role]);

  if (user?.role === 'admin') {
    return <Navigate to="/admin/dashboard" replace />;
  }

  const displayName = user?.name?.trim() || (role === 'teacher' ? '老师' : '同学');

  return (
    <PersonalHomeView
      role={role}
      displayName={displayName}
      data={data}
      loading={loading}
      onRetry={() => void load()}
    />
  );
}
