import React, { useEffect, useState } from 'react';
import { AdminLayout } from '@/modules/admin/components/AdminLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { StatCard } from '../../components/ui/StatCard';
import {
  Users,
  GraduationCap,
  Activity,
  Settings,
  Shield,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/Tabs';
import { UserGrowthChart } from '../../components/charts';
import { SecurityLogModal } from '@/modules/admin/components/SecurityLogModal';
import { useAppDispatch, useAppSelector } from '../../store';
import {
  fetchOverviewStats,
  fetchUserGrowth,
  fetchRecentActivities,
  fetchSystemStatus,
  setUserGrowthPeriod,
} from '@/modules/admin/store/adminStatsSlice';
import {
  selectOverviewData,
  selectUserGrowthData,
  selectActivitiesData,
  selectSystemStatusData,
} from '../../store/selectors/adminStatsSelectors';
import type { UserGrowthPeriod } from '@/modules/admin/types/adminStats';

export const AdminDashboardPage: React.FC = () => {
  const dispatch = useAppDispatch();

  // 安全日志弹窗状态
  const [isSecurityLogModalOpen, setIsSecurityLogModalOpen] = useState(false);

  // 使用记忆化 Selectors 减少不必要的重渲染
  const { overview, overviewLoading } = useAppSelector(selectOverviewData);
  const { userGrowth, userGrowthLoading, userGrowthPeriod } = useAppSelector(selectUserGrowthData);
  const { recentActivities, activitiesLoading } = useAppSelector(selectActivitiesData);
  const { systemStatus, systemStatusLoading } = useAppSelector(selectSystemStatusData);

  // 组件挂载时获取一次性数据
  useEffect(() => {
    dispatch(fetchOverviewStats());
    dispatch(fetchRecentActivities(10));
    dispatch(fetchSystemStatus());
  }, [dispatch]);

  // 仅在 period 变化时获取用户增长数据
  useEffect(() => {
    dispatch(fetchUserGrowth(userGrowthPeriod));
  }, [dispatch, userGrowthPeriod]);

  // 刷新所有数据
  const handleRefresh = () => {
    dispatch(fetchOverviewStats());
    dispatch(fetchUserGrowth(userGrowthPeriod));
    dispatch(fetchRecentActivities(10));
    dispatch(fetchSystemStatus());
  };

  // 切换用户增长周期
  const handlePeriodChange = (period: UserGrowthPeriod) => {
    dispatch(setUserGrowthPeriod(period));
    dispatch(fetchUserGrowth(period));
  };

  // 格式化数字显示
  const formatNumber = (num: number | undefined): string => {
    if (num === undefined) return '-';
    return num.toLocaleString();
  };

  // 格式化趋势显示
  const formatTrend = (value: number | undefined): string => {
    if (value === undefined) return '';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  };

  return (
    <AdminLayout>
      <div className="container mx-auto max-w-7xl">
        <div className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-2">管理员控制台</h1>
            <p className="text-surface-500 dark:text-surface-400">系统概览与管理功能</p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={handleRefresh}>
              <RefreshCw className={`w-4 h-4 mr-2 ${overviewLoading === 'loading' ? 'animate-spin' : ''}`} />
              刷新数据
            </Button>
            <Button onClick={() => setIsSecurityLogModalOpen(true)}>
              <Shield className="w-4 h-4 mr-2" />
              安全日志
            </Button>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
          <StatCard
            title="总用户数"
            value={overviewLoading === 'loading' ? '...' : formatNumber(overview?.total_users)}
            trend={formatTrend(overview?.trends.users_change)}
            trendUp={(overview?.trends.users_change ?? 0) >= 0}
            icon={<Users className="w-5 h-5 text-primary-600 dark:text-primary-400" />}
          />
          <StatCard
            title="学生账户"
            value={overviewLoading === 'loading' ? '...' : formatNumber(overview?.student_count)}
            trend={formatTrend(overview?.trends.students_change)}
            trendUp={(overview?.trends.students_change ?? 0) >= 0}
            icon={<GraduationCap className="w-5 h-5 text-secondary-600 dark:text-secondary-400" />}
          />
          <StatCard
            title="教师账户"
            value={overviewLoading === 'loading' ? '...' : formatNumber(overview?.teacher_count)}
            trend={formatTrend(overview?.trends.teachers_change)}
            trendUp={(overview?.trends.teachers_change ?? 0) >= 0}
            icon={<Users className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
          />
          <StatCard
            title="系统活跃度"
            value={overviewLoading === 'loading' ? '...' : `${overview?.active_rate ?? 0}%`}
            trend={formatTrend(overview?.trends.active_rate_change)}
            trendUp={(overview?.trends.active_rate_change ?? 0) >= 0}
            icon={<Activity className="w-5 h-5 text-orange-600 dark:text-orange-400" />}
          />
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">系统概览</TabsTrigger>
            <TabsTrigger value="accounts">账户管理</TabsTrigger>
            <TabsTrigger value="ai-models">AI 模型</TabsTrigger>
            <TabsTrigger value="system">系统状态</TabsTrigger>
          </TabsList>

          {/* 系统概览 Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 最近活动 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">最近活动</CardTitle>
                </CardHeader>
                <CardContent>
                  {activitiesLoading === 'loading' ? (
                    <div className="space-y-4">
                      {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="flex items-start space-x-3 animate-pulse">
                          <div className="w-2 h-2 rounded-full mt-2 bg-surface-300 dark:bg-surface-600" />
                          <div className="flex-1 space-y-2">
                            <div className="h-4 bg-surface-200 dark:bg-surface-700 rounded w-3/4" />
                            <div className="h-3 bg-surface-200 dark:bg-surface-700 rounded w-1/4" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : recentActivities.length > 0 ? (
                    <div className="space-y-4">
                      {recentActivities.map((activity) => (
                        <ActivityItem
                          key={activity.id}
                          user={activity.user_name}
                          action={activity.action_display}
                          time={formatRelativeTime(activity.timestamp)}
                          type={activity.type}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-surface-500 dark:text-surface-400">
                      暂无活动记录
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* 系统警告 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">系统警告</CardTitle>
                </CardHeader>
                <CardContent>
                  {systemStatusLoading === 'loading' ? (
                    <div className="space-y-4">
                      {[1, 2, 3].map((i) => (
                        <div key={i} className="p-4 rounded-lg border border-surface-200 dark:border-surface-700 animate-pulse">
                          <div className="flex items-start space-x-3">
                            <div className="w-5 h-5 rounded bg-surface-300 dark:bg-surface-600" />
                            <div className="flex-1 space-y-2">
                              <div className="h-4 bg-surface-200 dark:bg-surface-700 rounded w-1/2" />
                              <div className="h-3 bg-surface-200 dark:bg-surface-700 rounded w-3/4" />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : systemStatus?.alerts && systemStatus.alerts.length > 0 ? (
                    <div className="space-y-4">
                      {systemStatus.alerts.map((alert) => (
                        <AlertItem
                          key={alert.id}
                          title={alert.title}
                          description={alert.description}
                          severity={alert.severity}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-surface-500 dark:text-surface-400">
                      暂无系统警告
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* 用户增长图表 */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-xl">用户增长趋势</CardTitle>
                <div className="flex gap-2">
                  {(['7d', '30d', '90d'] as UserGrowthPeriod[]).map((period) => (
                    <Button
                      key={period}
                      variant={userGrowthPeriod === period ? 'primary' : 'outline'}
                      size="sm"
                      onClick={() => handlePeriodChange(period)}
                    >
                      {period === '7d' ? '7 天' : period === '30d' ? '30 天' : '90 天'}
                    </Button>
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                {userGrowth?.data && userGrowth.data.length > 0 ? (
                  <>
                    <UserGrowthChart
                      data={userGrowth.data}
                      height={300}
                      loading={userGrowthLoading === 'loading'}
                    />
                    {userGrowth.summary && (
                      <div className="mt-4 flex justify-center gap-8 text-sm text-surface-600 dark:text-surface-400">
                        <div>
                          <span className="font-medium">期间新增用户：</span>
                          <span className="text-primary-600 dark:text-primary-400 font-semibold ml-1">
                            {userGrowth.summary.total_new_users.toLocaleString()}
                          </span>
                        </div>
                        <div>
                          <span className="font-medium">日均增长：</span>
                          <span className="text-emerald-600 dark:text-emerald-400 font-semibold ml-1">
                            {userGrowth.summary.avg_daily_growth.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    )}
                  </>
                ) : userGrowthLoading === 'loading' ? (
                  <div className="h-64 flex items-center justify-center">
                    <div className="text-surface-500 dark:text-surface-400">加载中...</div>
                  </div>
                ) : (
                  <div className="h-64 flex items-center justify-center bg-surface-50 dark:bg-surface-800 rounded-lg border-2 border-dashed border-surface-200 dark:border-surface-700">
                    <div className="text-center text-surface-500 dark:text-surface-400">
                      暂无数据
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 账户管理 Tab */}
          <TabsContent value="accounts" className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-xl">账户列表</CardTitle>
                <Button>添加账户</Button>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12 text-surface-500 dark:text-surface-400">
                  <Users className="w-12 h-12 mx-auto mb-3" />
                  <p>账户管理功能将在独立页面实现</p>
                  <Button variant="outline" className="mt-4">
                    前往账户管理页面
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI 模型 Tab */}
          <TabsContent value="ai-models" className="space-y-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-xl">AI 模型配置</CardTitle>
                <Button>添加模型</Button>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12 text-surface-500 dark:text-surface-400">
                  <Settings className="w-12 h-12 mx-auto mb-3" />
                  <p>AI 模型设置功能将在独立页面实现</p>
                  <Button variant="outline" className="mt-4">
                    前往 AI 模型设置页面
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 系统状态 Tab */}
          <TabsContent value="system" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">服务状态</CardTitle>
                </CardHeader>
                <CardContent>
                  {systemStatusLoading === 'loading' ? (
                    <div className="space-y-3">
                      {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="flex items-center justify-between py-2 animate-pulse">
                          <div className="h-4 bg-surface-200 dark:bg-surface-700 rounded w-1/3" />
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 rounded-full bg-surface-300 dark:bg-surface-600" />
                            <div className="h-3 bg-surface-200 dark:bg-surface-700 rounded w-12" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : systemStatus?.services ? (
                    <div className="space-y-3">
                      {systemStatus.services.map((service, index) => (
                        <ServiceStatusItem
                          key={index}
                          name={service.name}
                          status={service.status}
                          latency={service.latency_ms}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-surface-500 dark:text-surface-400">
                      无法获取服务状态
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-xl">系统警告</CardTitle>
                </CardHeader>
                <CardContent>
                  {systemStatusLoading === 'loading' ? (
                    <div className="space-y-3">
                      {[1, 2].map((i) => (
                        <div key={i} className="animate-pulse p-4 rounded-lg border border-surface-200 dark:border-surface-700">
                          <div className="h-4 bg-surface-200 dark:bg-surface-700 rounded w-1/3 mb-2" />
                          <div className="h-3 bg-surface-200 dark:bg-surface-700 rounded w-2/3" />
                        </div>
                      ))}
                    </div>
                  ) : systemStatus?.alerts && systemStatus.alerts.length > 0 ? (
                    <div className="space-y-3">
                      {systemStatus.alerts.map((alert) => (
                        <AlertItem
                          key={alert.id}
                          title={alert.title}
                          description={alert.description}
                          severity={alert.severity}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-surface-500 dark:text-surface-400">
                      暂无系统警告
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* 安全日志弹窗 */}
      <SecurityLogModal
        isOpen={isSecurityLogModalOpen}
        onClose={() => setIsSecurityLogModalOpen(false)}
      />
    </AdminLayout>
  );
};

// 格式化相对时间
const formatRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const time = new Date(timestamp);
  const diffMs = now.getTime() - time.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins} 分钟前`;
  if (diffHours < 24) return `${diffHours} 小时前`;
  if (diffDays < 7) return `${diffDays} 天前`;
  return time.toLocaleDateString('zh-CN');
};

// 活动项组件
const ActivityItem = ({ user, action, time, type }: {
  user: string;
  action: string;
  time: string;
  type: 'success' | 'info' | 'warning';
}) => {
  const colorMap = {
    success: 'bg-emerald-500',
    info: 'bg-blue-500',
    warning: 'bg-orange-500',
  };

  return (
    <div className="flex items-start space-x-3">
      <div className={`w-2 h-2 rounded-full mt-2 ${colorMap[type]}`} />
      <div className="flex-1">
        <div className="text-sm text-surface-900 dark:text-surface-100">
          <span className="font-medium">{user}</span> {action}
        </div>
        <div className="text-xs text-surface-500 dark:text-surface-400 mt-0.5">{time}</div>
      </div>
    </div>
  );
};

// 警告项组件
const AlertItem = ({ title, description, severity }: {
  title: string;
  description: string;
  severity: 'error' | 'warning' | 'info';
}) => {
  const colorMap = {
    error: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    warning: 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
    info: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
  };

  return (
    <div className={`p-4 rounded-lg border ${colorMap[severity]}`}>
      <div className="flex items-start space-x-3">
        <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
        <div className="flex-1">
          <div className="font-medium text-sm">{title}</div>
          <div className="text-xs mt-1 opacity-90">{description}</div>
        </div>
      </div>
    </div>
  );
};

// 服务状态组件
const ServiceStatusItem = ({ name, status, latency }: {
  name: string;
  status: 'running' | 'stopped' | 'warning';
  latency?: number | null;
}) => {
  const statusConfig = {
    running: { color: 'bg-emerald-500', text: '运行中' },
    stopped: { color: 'bg-red-500', text: '已停止' },
    warning: { color: 'bg-orange-500', text: '异常' },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-surface-900 dark:text-surface-100">{name}</span>
      <div className="flex items-center space-x-3">
        {latency !== null && latency !== undefined && (
          <span className="text-xs text-surface-400">{latency.toFixed(0)}ms</span>
        )}
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${config.color}`} />
          <span className="text-xs text-surface-500 dark:text-surface-400">{config.text}</span>
        </div>
      </div>
    </div>
  );
};


