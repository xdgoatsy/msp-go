import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { MainLayout } from '../../components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import {
  Users,
  Search,
  TrendingUp,
  TrendingDown,
  Eye,

} from 'lucide-react';
import { classService } from '@/modules/classroom/services/classService';
import { teacherService } from '@/modules/teacher/services/teacherService';
import type { ClassInfo, ClassStudent } from '@/modules/classroom/types/classroom';
import type { StudentsStats } from '@/modules/teacher/types/teacher';

type StudentRow = ClassStudent & {
  classId: string;
  className: string;
};

export const StudentsPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClassId, setSelectedClassId] = useState('all');
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [stats, setStats] = useState<StudentsStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    const loadClasses = async () => {
      try {
        const response = await classService.listTeacherClasses();
        setClasses(response.items);
      } catch {
        setErrorMessage('班级列表加载失败，请稍后重试');
      }
    };
    loadClasses();
  }, []);

  useEffect(() => {
    const loadStats = async () => {
      try {
        setStatsLoading(true);
        const data = await teacherService.getStudentsStats();
        setStats(data);
      } catch (err) {
        console.error('获取学生统计数据失败:', err);
      } finally {
        setStatsLoading(false);
      }
    };
    loadStats();
  }, []);

  useEffect(() => {
    const loadStudents = async () => {
      if (classes.length === 0) {
        setStudents([]);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setErrorMessage('');
      try {
        if (selectedClassId === 'all') {
          const details = await Promise.all(
            classes.map((cls) => classService.getTeacherClassDetail(cls.id))
          );
          const merged = details.flatMap((detail) =>
            detail.students.map((student) => ({
              ...student,
              classId: detail.class_info.id,
              className: detail.class_info.name,
            }))
          );
          setStudents(merged);
        } else {
          const detail = await classService.getTeacherClassDetail(selectedClassId);
          setStudents(
            detail.students.map((student) => ({
              ...student,
              classId: detail.class_info.id,
              className: detail.class_info.name,
            }))
          );
        }
      } catch {
        setErrorMessage('学生列表加载失败，请稍后重试');
      } finally {
        setIsLoading(false);
      }
    };
    loadStudents();
  }, [classes, selectedClassId]);

  // 使用 useMemo 缓存过滤结果，避免每次渲染重新计算
  const filteredStudents = useMemo(() => {
    return students.filter(student => {
      const displayName = student.display_name || student.username || '';
      const matchesSearch = displayName.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesClass = selectedClassId === 'all' || student.classId === selectedClassId;
      return matchesSearch && matchesClass;
    });
  }, [searchTerm, selectedClassId, students]);

  return (
    <MainLayout>
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* 页面标题 */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100 mb-1">学生管理</h1>
            <p className="text-surface-500 dark:text-surface-400">管理和查看所有学生的学习情况</p>
          </div>
          <div className="flex gap-3">
            <Link to="/teacher/classes">
              <Button variant="outline" size="sm">
                查看班级管理
              </Button>
            </Link>

          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary-50 dark:bg-primary-900/30 rounded-lg">
                  <Users className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                    {statsLoading ? '...' : stats?.total_students || 0}
                  </div>
                  <div className="text-sm text-surface-500">总学生数</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-50 dark:bg-emerald-900/30 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                    {statsLoading ? '...' : stats?.avg_score || 0}
                  </div>
                  <div className="text-sm text-surface-500">平均成绩</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-secondary-50 dark:bg-secondary-900/30 rounded-lg">
                  <Users className="w-5 h-5 text-secondary-600 dark:text-secondary-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                    {statsLoading ? '...' : `${stats?.active_today || 0}%`}
                  </div>
                  <div className="text-sm text-surface-500">今日活跃率</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-50 dark:bg-amber-900/30 rounded-lg">
                  <TrendingDown className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-surface-900 dark:text-surface-100">
                    {statsLoading ? '...' : stats?.need_attention || 0}
                  </div>
                  <div className="text-sm text-surface-500">需关注学生</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 筛选和搜索 */}
        <Card className="mb-6">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
                <Input
                  placeholder="搜索学生姓名..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={selectedClassId}
                  onChange={(e) => setSelectedClassId(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="all">全部班级</option>
                  {classes.map((cls) => (
                    <option key={cls.id} value={cls.id}>{cls.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 学生列表 */}
        <Card>
          <CardHeader>
            <CardTitle>学生列表 ({filteredStudents.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {errorMessage && (
              <p className="mb-4 text-sm text-red-500">{errorMessage}</p>
            )}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-200 dark:border-surface-700">
                    <th className="text-left py-3 px-4 font-medium text-surface-500 dark:text-surface-400">学生</th>
                    <th className="text-left py-3 px-4 font-medium text-surface-500 dark:text-surface-400">班级</th>
                    <th className="text-left py-3 px-4 font-medium text-surface-500 dark:text-surface-400">邮箱</th>
                    <th className="text-right py-3 px-4 font-medium text-surface-500 dark:text-surface-400">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                  {isLoading ? (
                    <tr>
                      <td className="py-6 px-4 text-surface-500 dark:text-surface-400" colSpan={4}>
                        正在加载学生数据...
                      </td>
                    </tr>
                  ) : filteredStudents.length === 0 ? (
                    <tr>
                      <td className="py-6 px-4 text-surface-500 dark:text-surface-400" colSpan={4}>
                        暂无学生
                      </td>
                    </tr>
                  ) : (
                    filteredStudents.map((student) => (
                      <tr key={student.id} className="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-full bg-linear-to-br from-primary-100 to-secondary-100 dark:from-primary-900 dark:to-secondary-900 flex items-center justify-center text-primary-700 dark:text-primary-300 font-medium text-sm">
                              {(student.display_name || student.username || '—')[0]}
                            </div>
                            <span className="font-medium text-surface-900 dark:text-surface-100">
                              {student.display_name || student.username || '未知学生'}
                            </span>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-surface-600 dark:text-surface-400">{student.className}</td>
                        <td className="py-4 px-4 text-surface-600 dark:text-surface-400">{student.email}</td>
                        <td className="py-4 px-4">
                          <div className="flex justify-end gap-1">
                            <Link to={`/teacher/student/${student.id}`}>
                              <Button variant="ghost" size="icon" className="h-8 w-8" title="查看详情">
                                <Eye className="w-4 h-4" />
                              </Button>
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {!isLoading && filteredStudents.length === 0 && (
              <div className="text-center py-12">
                <Users className="w-12 h-12 text-surface-300 dark:text-surface-600 mx-auto mb-4" />
                <p className="text-surface-500 dark:text-surface-400">没有找到匹配的学生</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
};

export default StudentsPage;
