import React, { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '../../components/layout/MainLayout';
import { Card, CardContent, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Progress } from '../../components/ui/Progress';
import { Tabs, TabsList, TabsTrigger } from '../../components/ui/Tabs';
import {
  Plus,
  Calendar,
  Clock,
  Users,
  CheckCircle2,
  AlertCircle,
  FileText,
  MoreHorizontal,
  Edit,
  Eye,
  Copy,
  Loader2,
} from 'lucide-react';
import { assignmentService } from '@/modules/teacher/services/assignmentService';
import type { Assignment } from '@/modules/teacher/services/assignmentService';

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'active':
      return <Badge variant="success">进行中</Badge>;
    case 'ended':
      return <Badge variant="secondary">已截止</Badge>;
    case 'draft':
      return <Badge variant="outline">草稿</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
};

export const AssignmentsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, active: 0, pending: 0 });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [listRes, statsRes] = await Promise.all([
        assignmentService.list({ status: activeTab === 'all' ? undefined : activeTab }),
        assignmentService.getStats(),
      ]);
      setAssignments(listRes.items);
      setStats(statsRes);
    } catch {
      // API 尚未实现时，显示空列表
      setAssignments([]);
      setStats({ total: 0, active: 0, pending: 0 });
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <MainLayout>
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* 页面标题 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-2">
              作业管理
            </h1>
            <p className="text-surface-500 dark:text-surface-400">
              创建和管理班级作业，跟踪学生完成情况
            </p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            新建作业
          </Button>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                  <FileText className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <div className="text-3xl font-bold text-surface-900 dark:text-surface-100">{stats.total}</div>
                  <div className="text-sm text-surface-500 dark:text-surface-400">作业总数</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                  <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <div className="text-3xl font-bold text-surface-900 dark:text-surface-100">{stats.active}</div>
                  <div className="text-sm text-surface-500 dark:text-surface-400">进行中</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
                  <AlertCircle className="h-6 w-6 text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  <div className="text-3xl font-bold text-surface-900 dark:text-surface-100">{stats.pending}</div>
                  <div className="text-sm text-surface-500 dark:text-surface-400">待批改</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 作业列表 */}
        <Card>
          <CardHeader>
            <Tabs defaultValue="all" onValueChange={setActiveTab}>
              <TabsList>
                <TabsTrigger value="all">全部</TabsTrigger>
                <TabsTrigger value="active">进行中</TabsTrigger>
                <TabsTrigger value="ended">已截止</TabsTrigger>
                <TabsTrigger value="draft">草稿</TabsTrigger>
              </TabsList>
            </Tabs>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
              </div>
            ) : (
            <div className="space-y-4">
              {assignments.map((assignment) => (
                <div
                  key={assignment.id}
                  className="p-6 rounded-lg border border-surface-200 dark:border-surface-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100">{assignment.title}</h3>
                        {getStatusBadge(assignment.status)}
                      </div>
                      <p className="text-sm text-surface-500 dark:text-surface-400 mb-4">{assignment.description}</p>
                      <div className="flex items-center gap-6 text-sm text-surface-500 dark:text-surface-400">
                        <div className="flex items-center gap-1"><FileText className="h-4 w-4" /><span>{assignment.questions} 道题目</span></div>
                        <div className="flex items-center gap-1"><Users className="h-4 w-4" /><span>{assignment.totalStudents} 名学生</span></div>
                        {assignment.dueDate && (<div className="flex items-center gap-1"><Calendar className="h-4 w-4" /><span>截止: {assignment.dueDate}</span></div>)}
                        <div className="flex items-center gap-1"><Clock className="h-4 w-4" /><span>创建于 {assignment.createdAt}</span></div>
                      </div>
                      {assignment.status !== 'draft' && (
                        <div className="mt-4 grid grid-cols-3 gap-4">
                          <div>
                            <div className="flex items-center justify-between text-sm mb-1">
                              <span className="text-surface-500 dark:text-surface-400">提交进度</span>
                              <span className="font-medium text-surface-700 dark:text-surface-300">{assignment.submitted}/{assignment.totalStudents}</span>
                            </div>
                            <Progress value={assignment.totalStudents > 0 ? (assignment.submitted / assignment.totalStudents) * 100 : 0} variant="default" size="sm" />
                          </div>
                          <div>
                            <div className="flex items-center justify-between text-sm mb-1">
                              <span className="text-surface-500 dark:text-surface-400">批改进度</span>
                              <span className="font-medium text-surface-700 dark:text-surface-300">{assignment.graded}/{assignment.submitted}</span>
                            </div>
                            <Progress value={assignment.submitted > 0 ? (assignment.graded / assignment.submitted) * 100 : 0} variant="success" size="sm" />
                          </div>
                          <div>
                            <div className="text-sm text-surface-500 dark:text-surface-400 mb-1">平均分</div>
                            <div className="text-xl font-bold text-surface-900 dark:text-surface-100">{assignment.averageScore !== null ? assignment.averageScore : '-'}</div>
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      {assignment.status === 'active' && <Button size="sm">开始批改</Button>}
                      {assignment.status === 'draft' && <Button size="sm">发布</Button>}
                      <Button variant="outline" size="icon" className="h-9 w-9"><Eye className="h-4 w-4" /></Button>
                      <Button variant="outline" size="icon" className="h-9 w-9"><Edit className="h-4 w-4" /></Button>
                      <Button variant="outline" size="icon" className="h-9 w-9"><Copy className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="h-9 w-9"><MoreHorizontal className="h-4 w-4" /></Button>
                    </div>
                  </div>
                </div>
              ))}

              {assignments.length === 0 && (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 mx-auto text-surface-400 mb-4" />
                  <h3 className="text-lg font-medium text-surface-900 dark:text-surface-100 mb-2">暂无作业</h3>
                  <p className="text-surface-500 dark:text-surface-400 mb-4">点击"新建作业"按钮创建第一个作业</p>
                  <Button><Plus className="h-4 w-4 mr-2" />新建作业</Button>
                </div>
              )}
            </div>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
};
