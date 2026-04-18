import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainLayout } from '../../components/layout/MainLayout';
import { Card, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import {
  Calendar,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Clock,
  AlertCircle,
  Link as LinkIcon,
  CloudOff
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../store';
import { syncClasstable, loadFromCache } from '@/modules/classroom/store/classtableSlice';
import {
  selectClasstableData,
  selectClasstableLoading,
  selectClasstableError,
  selectClasstableIsFromCache,
  selectClasstableLastSyncAt,
  selectClasstableCachedAt,
} from '@/store/selectors/classtableSelectors';
import { xidianService, type XidianBindingStatus } from '@/modules/xidian/services/xidianService';
import {
  calculateCurrentWeek,
  getClassesForWeek,
  calculateMathHours,
  getPeriodTimeRange,
  WEEKDAYS,
} from '../../libs/utils/classtableUtils';
import type { ClassCell } from '@/modules/classroom/types/classtable';

export const CourseOverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const data = useAppSelector(selectClasstableData);
  const loading = useAppSelector(selectClasstableLoading);
  const error = useAppSelector(selectClasstableError);
  const isFromCache = useAppSelector(selectClasstableIsFromCache);
  const lastSyncAt = useAppSelector(selectClasstableLastSyncAt);
  const cachedAt = useAppSelector(selectClasstableCachedAt);

  const [bindingStatus, setBindingStatus] = useState<XidianBindingStatus | null>(null);
  const [checkingBinding, setCheckingBinding] = useState(true);
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [currentWeek, setCurrentWeek] = useState(1);

  // 检查绑定状态并缓存优先加载
  useEffect(() => {
    const checkBinding = async () => {
      try {
        const status = await xidianService.getBindingStatus();
        setBindingStatus(status);
        if (status.is_bound) {
          // 仅加载本地缓存，课表同步由用户手动触发
          dispatch(loadFromCache());
        }
      } catch {
        setBindingStatus({ is_bound: false });
      } finally {
        setCheckingBinding(false);
      }
    };
    checkBinding();
  }, [dispatch]);

  // 计算当前周次
  useEffect(() => {
    if (data?.term_start_day) {
      const week = calculateCurrentWeek(data.term_start_day);
      const clampedWeek = Math.min(Math.max(1, week), data.semester_length || 20);
      setCurrentWeek(clampedWeek);
      setSelectedWeek(clampedWeek);
    }
  }, [data]);

  const handleSync = () => {
    dispatch(syncClasstable());
  };

  // 格式化同步时间
  const formatSyncTime = (isoString: string | null) => {
    if (!isoString) return null;
    try {
      return new Date(isoString).toLocaleString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return null;
    }
  };

  const handlePrevWeek = () => {
    setSelectedWeek((w) => Math.max(1, w - 1));
  };

  const handleNextWeek = () => {
    const maxWeek = data?.semester_length || 20;
    setSelectedWeek((w) => Math.min(maxWeek, w + 1));
  };

  // 未绑定状态
  if (!checkingBinding && !bindingStatus?.is_bound) {
    return (
      <MainLayout>
        <div className="container mx-auto px-6 py-12 max-w-4xl">
          <Card className="border-surface-200 dark:border-surface-700">
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <AlertCircle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
              </div>
              <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-3">
                尚未绑定西电账号
              </h2>
              <p className="text-surface-500 dark:text-surface-400 mb-8 max-w-md mx-auto">
                绑定西电教务账号后，可自动同步您的课表信息，查看高等数学课程安排和课时统计。
              </p>
              <Button
                variant="primary"
                size="lg"
                onClick={() => navigate('/profile')}
                className="inline-flex items-center gap-2"
              >
                <LinkIcon className="w-5 h-5" />
                前往绑定账号
              </Button>
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    );
  }

  // 加载中（仅在没有缓存数据时显示）
  if (checkingBinding) {
    return (
      <MainLayout>
        <div className="container mx-auto px-6 py-12 max-w-7xl">
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 animate-spin text-primary-500" />
            <span className="ml-3 text-surface-500">加载中...</span>
          </div>
        </div>
      </MainLayout>
    );
  }

  // 错误状态（仅在没有缓存数据时显示）
  if (error && !data) {
    return (
      <MainLayout>
        <div className="container mx-auto px-6 py-12 max-w-4xl">
          <Card className="border-red-200 dark:border-red-800">
            <CardContent className="p-8 text-center">
              <AlertCircle className="w-12 h-12 mx-auto mb-4 text-red-500" />
              <h2 className="text-xl font-semibold text-surface-900 dark:text-surface-100 mb-2">
                加载失败
              </h2>
              <p className="text-surface-500 dark:text-surface-400 mb-6">{error}</p>
              <Button variant="primary" onClick={handleSync}>
                重试
              </Button>
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    );
  }

  // 无缓存数据时提示同步
  if (!data && bindingStatus?.is_bound) {
    return (
      <MainLayout>
        <div className="container mx-auto px-6 py-12 max-w-4xl">
          <Card className="border-surface-200 dark:border-surface-700">
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <CloudOff className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-3">
                暂无课表数据
              </h2>
              <p className="text-surface-500 dark:text-surface-400 mb-8 max-w-md mx-auto">
                点击下方按钮从教务系统同步您的课表信息。
              </p>
              <Button
                variant="primary"
                size="lg"
                onClick={handleSync}
                disabled={loading}
                className="inline-flex items-center gap-2"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                {loading ? '同步中...' : '同步课表'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    );
  }

  const grid = data ? getClassesForWeek(data, selectedWeek) : [];
  const mathStats = data ? calculateMathHours(data, currentWeek) : null;

  return (
    <MainLayout>
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* 顶部信息栏 */}
        <div className="mb-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-1">
                我的课表
              </h1>
              <div className="flex items-center gap-2 text-surface-500 dark:text-surface-400">
                <span>{data?.semester_code || '当前学期'} · 第 {currentWeek} 周</span>
                {isFromCache && (lastSyncAt || cachedAt) && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">
                    数据来自缓存 · 最后同步于 {formatSyncTime(lastSyncAt || cachedAt)}
                  </span>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              onClick={handleSync}
              disabled={loading}
              className="inline-flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              {loading ? '同步中...' : '同步课表'}
            </Button>
          </div>

          {/* 统计卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <Card className="border-surface-200 dark:border-surface-700">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <BookOpen className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div>
                    <div className="text-sm text-surface-500 dark:text-surface-400">本周高数</div>
                    <div className="text-xl font-bold text-surface-900 dark:text-surface-100">
                      {mathStats?.weeklyHours || 0} 课时
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-surface-200 dark:border-surface-700">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <div className="text-sm text-surface-500 dark:text-surface-400">剩余课时</div>
                    <div className="text-xl font-bold text-surface-900 dark:text-surface-100">
                      {mathStats?.remainingHours || 0} / {mathStats?.totalHours || 0}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-surface-200 dark:border-surface-700">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                    <Calendar className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div>
                    <div className="text-sm text-surface-500 dark:text-surface-400">剩余周数</div>
                    <div className="text-xl font-bold text-surface-900 dark:text-surface-100">
                      {mathStats?.remainingWeeks || 0} / {mathStats?.totalWeeks || 0} 周
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 周次选择器 */}
          <div className="flex items-center justify-center gap-4 mb-4">
            <Button variant="ghost" size="sm" onClick={handlePrevWeek} disabled={selectedWeek <= 1}>
              <ChevronLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <span className="text-lg font-medium text-surface-900 dark:text-surface-100">
                第 {selectedWeek} 周
              </span>
              {selectedWeek === currentWeek && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">
                  本周
                </span>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleNextWeek}
              disabled={selectedWeek >= (data?.semester_length || 20)}
            >
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* 课表主体 */}
        <Card className="border-surface-200 dark:border-surface-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] border-collapse">
              <thead>
                <tr className="bg-surface-50 dark:bg-surface-800">
                  <th className="w-20 p-3 text-sm font-medium text-surface-500 dark:text-surface-400 border-b border-r border-surface-200 dark:border-surface-700">
                    节次
                  </th>
                  {WEEKDAYS.map((day, index) => (
                    <th
                      key={day}
                      className={`p-3 text-sm font-medium border-b border-surface-200 dark:border-surface-700 ${
                        index < 6 ? 'border-r' : ''
                      } ${
                        new Date().getDay() === (index + 1) % 7 || (index === 6 && new Date().getDay() === 0)
                          ? 'text-primary-600 dark:text-primary-400 bg-primary-50/50 dark:bg-primary-900/20'
                          : 'text-surface-500 dark:text-surface-400'
                      }`}
                    >
                      {day}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 12 }, (_, periodIndex) => (
                  <tr key={periodIndex}>
                    <td className="p-2 text-center border-r border-b border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800">
                      <div className="text-sm font-medium text-surface-700 dark:text-surface-300">
                        {periodIndex + 1}
                      </div>
                      <div className="text-xs text-surface-400 dark:text-surface-500">
                        {getPeriodTimeRange(periodIndex + 1).split('-')[0]}
                      </div>
                    </td>
                    {grid.map((dayClasses, dayIndex) => {
                      const cell = dayClasses[periodIndex];
                      const isFirstPeriod = cell && cell.startPeriod === periodIndex + 1;
                      const rowSpan = cell ? cell.endPeriod - cell.startPeriod + 1 : 1;

                      if (cell && !isFirstPeriod) return null;

                      return (
                        <td
                          key={dayIndex}
                          rowSpan={isFirstPeriod ? rowSpan : 1}
                          className={`p-1 border-b border-surface-200 dark:border-surface-700 ${
                            dayIndex < 6 ? 'border-r' : ''
                          } ${!cell ? 'bg-white dark:bg-surface-900' : ''}`}
                        >
                          {cell && isFirstPeriod && (
                            <ClassCellComponent cell={cell} />
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* 图例 */}
        <div className="mt-4 flex items-center justify-center gap-6 text-sm text-surface-500 dark:text-surface-400">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-blue-100 dark:bg-blue-900/50 border border-blue-300 dark:border-blue-700" />
            <span>高等数学</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-surface-100 dark:bg-surface-700 border border-surface-300 dark:border-surface-600" />
            <span>其他课程</span>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

/** 课程单元格组件 */
const ClassCellComponent: React.FC<{ cell: ClassCell }> = ({ cell }) => {
  const bgClass = cell.isMath
    ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800'
    : 'bg-surface-50 dark:bg-surface-800 border-surface-200 dark:border-surface-700';

  const textClass = cell.isMath
    ? 'text-blue-700 dark:text-blue-300'
    : 'text-surface-700 dark:text-surface-300';

  return (
    <div className={`h-full p-2 rounded border ${bgClass} text-xs`}>
      <div className={`font-medium truncate ${textClass}`} title={cell.name}>
        {cell.name}
      </div>
      <div className="text-surface-500 dark:text-surface-400 truncate mt-1" title={cell.classroom}>
        {cell.classroom}
      </div>
      <div className="text-surface-400 dark:text-surface-500 truncate" title={cell.teacher}>
        {cell.teacher}
      </div>
    </div>
  );
};
