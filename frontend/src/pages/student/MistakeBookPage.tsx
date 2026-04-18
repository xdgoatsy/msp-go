import React from 'react';
import { MainLayout } from '../../components/layout/MainLayout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Progress } from '../../components/ui/Progress';
import { Select } from '../../components/ui/Select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import {
  TrendingUp,
  BookOpen,
  Award,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  ArrowRight,
  Trash2,
  GraduationCap,
  Target,
  Sparkles,
  Link2,
  Clock,
  Loader2,
  User,
} from 'lucide-react';
import { MarkdownContent } from '../../components/chat/MarkdownContent';
import {
  useMistakeBook,
  parseScore,
  getDifficultyBadge,
  getErrorTypeLabel,
} from '@/modules/mistake/hooks/useMistakeBook';

/**
 * 成绩分析页面
 * 职责：纯 UI 渲染，业务逻辑由 useMistakeBook hook 提供
 */
export const MistakeBookPage: React.FC = () => {
  const {
    scores, scoresLoading, syncing, selectedSemester, bindingStatus, lastSyncAt,
    mistakes, pagination, mistakesLoading, mistakesError,
    portrait, portraitLoading, generating, clearing,
    filteredScores, semesterStats, overallStats, maxSemesterAvg,
    weakSubjects, semesterOptions, courseDistribution,
    setSelectedSemester, handleTabChange, handleSync,
    handleDeleteMistake, handleMarkAsMastered, handleFetchMistakes,
    handleGeneratePortrait, handleClearPortrait,
  } = useMistakeBook();

  return (
    <MainLayout>
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* 页面标题 */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-2">成绩分析</h1>
            <p className="text-surface-500 dark:text-surface-400">同步教务成绩，查看错题集，AI 生成个人学习画像。</p>
          </div>
          <Button onClick={handleSync} disabled={syncing} className="shadow-lg shadow-primary-500/20">
            {syncing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            {syncing ? '同步中...' : '同步成绩'}
          </Button>
        </div>

        {/* 统计卡片 */}
        {scores.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                  <TrendingUp className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                </div>
                <Badge variant={overallStats.weightedAvg >= 80 ? 'success' : 'warning'} className="text-xs">
                  {overallStats.weightedAvg >= 80 ? '良好' : '待提升'}
                </Badge>
              </div>
              <div className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-1">{overallStats.weightedAvg}</div>
              <div className="text-sm text-surface-500 dark:text-surface-400">加权平均分</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-secondary-100 dark:bg-secondary-900/30 flex items-center justify-center">
                  <GraduationCap className="h-6 w-6 text-secondary-600 dark:text-secondary-400" />
                </div>
              </div>
              <div className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-1">{overallStats.totalCredits}</div>
              <div className="text-sm text-surface-500 dark:text-surface-400">总学分</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
                  <Target className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <Badge variant={overallStats.passRate >= 90 ? 'success' : 'warning'} className="text-xs">{overallStats.passRate}%</Badge>
              </div>
              <div className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-1">{overallStats.passRate}%</div>
              <div className="text-sm text-surface-500 dark:text-surface-400">通过率</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
                  <BookOpen className="h-6 w-6 text-orange-600 dark:text-orange-400" />
                </div>
              </div>
              <div className="text-3xl font-bold text-surface-900 dark:text-surface-100 mb-1">{overallStats.totalCourses}</div>
              <div className="text-sm text-surface-500 dark:text-surface-400">科目总数</div>
            </CardContent>
          </Card>
        </div>
        )}

        {/* 主内容区 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* 左侧主内容 */}
          <div className="lg:col-span-8">
            <Tabs defaultValue="scores" onValueChange={handleTabChange}>
              <TabsList className="mb-6">
                <TabsTrigger value="scores">成绩分析</TabsTrigger>
                <TabsTrigger value="mistakes">错题集</TabsTrigger>
                <TabsTrigger value="portrait">学生画像</TabsTrigger>
              </TabsList>

              {/* Tab 1: 成绩分析 */}
              <TabsContent value="scores">
                {scoresLoading ? (
                  <div className="flex justify-center items-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
                    <span className="ml-3 text-surface-500">加载成绩数据...</span>
                  </div>
                ) : scores.length === 0 ? (
                  <Card>
                    <CardContent className="p-12 text-center">
                      <GraduationCap className="w-16 h-16 mx-auto mb-4 text-surface-300 dark:text-surface-600" />
                      <h3 className="text-lg font-semibold text-surface-700 dark:text-surface-300 mb-2">
                        暂无成绩数据
                      </h3>
                      <p className="text-sm text-surface-500 dark:text-surface-400 mb-6">
                        {bindingStatus?.is_bound
                          ? '请点击右上角「同步成绩」按钮从教务系统获取成绩。'
                          : '请先绑定西电教务系统账号，再同步成绩数据。'}
                      </p>
                      {bindingStatus?.is_bound && (
                        <Button onClick={handleSync} disabled={syncing}>
                          <RefreshCw className="w-4 h-4 mr-2" />
                          同步成绩
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                ) : (
                <div className="space-y-6">
                  {/* 学期筛选 */}
                  <div className="flex items-center gap-4">
                    <Select options={semesterOptions} value={selectedSemester} onChange={setSelectedSemester} className="w-48" />
                    <span className="text-sm text-surface-500 dark:text-surface-400">
                      共 {filteredScores.length} 门课程
                    </span>
                  </div>

                  {/* 成绩趋势图 */}
                  {semesterStats.length > 1 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <TrendingUp className="h-5 w-5 text-primary-500" />
                          学期成绩趋势
                        </CardTitle>
                        <CardDescription>各学期加权平均分变化</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-end justify-between h-48 gap-3 pt-4">
                          {semesterStats.map((stat, index) => (
                            <div key={index} className="flex-1 flex flex-col items-center">
                              <div className="w-full flex flex-col items-center justify-end h-36">
                                <div className="text-xs font-medium text-surface-700 dark:text-surface-300 mb-1">
                                  {stat.weightedAvg}
                                </div>
                                <div
                                  className="w-full max-w-12 bg-primary-500 dark:bg-primary-400 rounded-t-md transition-all hover:bg-primary-600"
                                  style={{ height: `${(stat.weightedAvg / maxSemesterAvg) * 100}%` }}
                                />
                              </div>
                              <div className="text-xs text-surface-500 dark:text-surface-400 mt-2 text-center">
                                {stat.semester.replace(/(\d{4}-\d{4})-(\d)/, '$1\n第$2学期')}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* 成绩明细表 */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Award className="h-5 w-5 text-primary-500" />
                        成绩明细
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-surface-200 dark:border-surface-700">
                              <th className="text-left py-3 px-2 font-medium text-surface-500 dark:text-surface-400">课程名称</th>
                              <th className="text-center py-3 px-2 font-medium text-surface-500 dark:text-surface-400">学分</th>
                              <th className="text-center py-3 px-2 font-medium text-surface-500 dark:text-surface-400">成绩</th>
                              <th className="text-center py-3 px-2 font-medium text-surface-500 dark:text-surface-400">课程类型</th>
                              <th className="text-center py-3 px-2 font-medium text-surface-500 dark:text-surface-400">状态</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredScores.map((item, idx) => {
                              const num = parseScore(item.score);
                              return (
                                <tr key={idx} className="border-b border-surface-100 dark:border-surface-800 hover:bg-surface-50 dark:hover:bg-surface-800/50">
                                  <td className="py-3 px-2 font-medium text-surface-900 dark:text-surface-100">{item.name}</td>
                                  <td className="py-3 px-2 text-center text-surface-600 dark:text-surface-400">{item.credit ?? '-'}</td>
                                  <td className="py-3 px-2 text-center">
                                    <span className={`font-bold ${
                                      !isNaN(num) && num >= 90 ? 'text-emerald-600 dark:text-emerald-400' :
                                      !isNaN(num) && num >= 80 ? 'text-primary-600 dark:text-primary-400' :
                                      !isNaN(num) && num >= 70 ? 'text-yellow-600 dark:text-yellow-400' :
                                      !isNaN(num) && num >= 60 ? 'text-orange-600 dark:text-orange-400' :
                                      'text-red-600 dark:text-red-400'
                                    }`}>
                                      {item.score ?? item.level ?? '-'}
                                    </span>
                                  </td>
                                  <td className="py-3 px-2 text-center">
                                    <Badge variant="outline" className="text-xs">{item.class_status ?? '-'}</Badge>
                                  </td>
                                  <td className="py-3 px-2 text-center">
                                    {item.is_passed === '1' ? (
                                      <Badge variant="success" className="text-xs">通过</Badge>
                                    ) : (
                                      <Badge variant="destructive" className="text-xs">未通过</Badge>
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>

                </div>
                )}
              </TabsContent>

              {/* Tab 2: 错题集 */}
              <TabsContent value="mistakes">
                <div className="space-y-4">
                  {/* 加载状态 */}
                  {mistakesLoading === 'loading' && (
                    <div className="flex justify-center items-center py-12">
                      <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
                      <span className="ml-3 text-surface-500">加载错题中...</span>
                    </div>
                  )}

                  {/* 错误状态 */}
                  {mistakesLoading === 'error' && mistakesError && (
                    <Card className="border-red-200 dark:border-red-800">
                      <CardContent className="p-6 text-center">
                        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
                        <p className="text-red-600 dark:text-red-400">{mistakesError}</p>
                        <Button
                          onClick={() => handleFetchMistakes(1)}
                          variant="outline"
                          className="mt-4"
                        >
                          重试
                        </Button>
                      </CardContent>
                    </Card>
                  )}

                  {/* 空状态 */}
                  {mistakesLoading === 'success' && mistakes.length === 0 && (
                    <Card>
                      <CardContent className="p-12 text-center">
                        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                        <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">
                          太棒了！暂无错题
                        </h3>
                        <p className="text-surface-500 dark:text-surface-400">
                          继续保持，多做练习巩固知识点
                        </p>
                      </CardContent>
                    </Card>
                  )}

                  {/* 错题列表 */}
                  {mistakesLoading === 'success' && mistakes.map((item) => {
                    const difficultyBadge = getDifficultyBadge(item.exercise.difficulty);
                    const masteryPercent = Math.round(item.mastery.current * 100);

                    return (
                      <Card key={item.id} className="hover:shadow-md transition-shadow border-surface-200 dark:border-surface-700">
                        <CardContent className="p-5">
                          <div className="flex justify-between items-start">
                            <div className="space-y-2 flex-1">
                              <div className="flex items-center space-x-3">
                                <Badge variant="outline" className="text-xs">
                                  {item.exercise.knowledgePoints?.[0] || '未分类'}
                                </Badge>
                                <Badge variant={difficultyBadge.variant} className="text-xs">
                                  {difficultyBadge.label}
                                </Badge>
                                {item.diagnosis.errorType && (
                                  <Badge variant="secondary" className="text-xs">
                                    {getErrorTypeLabel(item.diagnosis.errorType)}
                                  </Badge>
                                )}
                              </div>
                              <h3 className="text-base font-semibold text-surface-900 dark:text-surface-100">
                                {item.exercise.title}
                              </h3>
                              <div className="flex items-center text-sm text-surface-500 dark:text-surface-400 space-x-4">
                                <div className="flex items-center">
                                  <AlertCircle className="w-3.5 h-3.5 mr-1 text-orange-500" />
                                  <span>{item.diagnosis.explanation || '暂无诊断'}</span>
                                </div>
                                {item.attempt.submittedAt && (
                                  <div className="flex items-center">
                                    <Clock className="w-3.5 h-3.5 mr-1 text-primary-500" />
                                    <span>{new Date(item.attempt.submittedAt).toLocaleDateString()}</span>
                                  </div>
                                )}
                                <div className="flex items-center">
                                  <RefreshCw className="w-3.5 h-3.5 mr-1 text-blue-500" />
                                  <span>错误 {item.errorCount} 次</span>
                                </div>
                              </div>
                            </div>
                            <div className="ml-4 flex flex-col items-end space-y-3">
                              <div className="text-right">
                                <div className="text-xs text-surface-500 dark:text-surface-400 mb-1">掌握度</div>
                                <Progress
                                  value={masteryPercent}
                                  variant={masteryPercent < 60 ? 'destructive' : masteryPercent < 80 ? 'warning' : 'success'}
                                  size="sm"
                                  className="w-20"
                                />
                                <div className="text-xs text-surface-600 dark:text-surface-300 mt-1">
                                  {masteryPercent}%
                                </div>
                              </div>
                              <div className="flex space-x-2">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="text-surface-400 hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-900/30"
                                  onClick={() => handleDeleteMistake(item.id)}
                                  title="删除错题"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleMarkAsMastered(item.id)}
                                  title="标记已掌握"
                                >
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  已掌握
                                </Button>
                                <Button size="sm">
                                  重做 <ArrowRight className="w-3 h-3 ml-1" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}

                  {/* 分页 */}
                  {mistakesLoading === 'success' && pagination.totalPages > 1 && (
                    <div className="flex justify-center items-center gap-2 mt-6">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={pagination.page === 1}
                        onClick={() => handleFetchMistakes(pagination.page - 1)}
                      >
                        上一页
                      </Button>
                      <span className="text-sm text-surface-600 dark:text-surface-400">
                        第 {pagination.page} / {pagination.totalPages} 页
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={pagination.page === pagination.totalPages}
                        onClick={() => handleFetchMistakes(pagination.page + 1)}
                      >
                        下一页
                      </Button>
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Tab 3: 学生画像 */}
              <TabsContent value="portrait">
                <div className="space-y-6">
                  {generating ? (
                    <Card>
                      <CardContent className="p-12">
                        <div className="text-center">
                          <Loader2 className="h-12 w-12 mx-auto mb-4 animate-spin text-primary-500" />
                          <p className="text-lg font-medium text-surface-700 dark:text-surface-300 mb-2">AI 正在生成学生画像...</p>
                          <p className="text-sm text-surface-500 dark:text-surface-400">正在分析你的学习数据，请稍候</p>
                        </div>
                      </CardContent>
                    </Card>
                  ) : portraitLoading === 'loading' ? (
                    <Card>
                      <CardContent className="p-12">
                        <div className="text-center">
                          <Loader2 className="h-8 w-8 mx-auto mb-3 animate-spin text-surface-400" />
                          <p className="text-surface-500 dark:text-surface-400">加载中...</p>
                        </div>
                      </CardContent>
                    </Card>
                  ) : portrait?.has_content ? (
                    <>
                      <Card>
                        <CardHeader>
                          <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2">
                              <User className="h-5 w-5 text-primary-500" />
                              学生画像
                            </CardTitle>
                            <div className="flex items-center gap-2">
                              {portrait.portrait_generated_at && (
                                <span className="text-xs text-surface-400 dark:text-surface-500 flex items-center gap-1">
                                  <Clock className="w-3.5 h-3.5" />
                                  {new Date(portrait.portrait_generated_at).toLocaleString('zh-CN')}
                                </span>
                              )}
                              <Button size="sm" variant="outline" onClick={handleGeneratePortrait} disabled={generating}>
                                <RefreshCw className="w-4 h-4 mr-1" />
                                重新生成
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/30"
                                onClick={handleClearPortrait}
                                disabled={clearing}
                              >
                                <Trash2 className="w-4 h-4 mr-1" />
                                清除
                              </Button>
                            </div>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="prose prose-sm dark:prose-invert max-w-none">
                            <MarkdownContent content={portrait.portrait_content!} unwrapOuterFence />
                          </div>
                        </CardContent>
                      </Card>
                    </>
                  ) : (
                    <Card>
                      <CardContent className="p-12">
                        <div className="text-center">
                          <User className="h-16 w-16 mx-auto mb-4 text-surface-300 dark:text-surface-600" />
                          <h3 className="text-lg font-semibold text-surface-700 dark:text-surface-300 mb-2">尚未生成学生画像</h3>
                          <p className="text-sm text-surface-500 dark:text-surface-400 mb-6 max-w-md mx-auto">
                            AI 将根据你的学习数据、成绩记录和做题情况，生成个性化的学习画像分析报告，帮助你了解自身学习状况。
                          </p>
                          <Button onClick={handleGeneratePortrait} disabled={generating}>
                            <Sparkles className="w-4 h-4 mr-2" />
                            生成画像
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </div>

          {/* 右侧边栏 */}
          <div className="lg:col-span-4 space-y-6">
            {/* 同步状态 */}
            <Card className="bg-linear-to-br from-primary-600 to-primary-700 text-white border-none shadow-lg shadow-primary-900/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Link2 className="h-5 w-5" />
                  教务系统
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-primary-100 text-sm">绑定状态</span>
                    <Badge variant={bindingStatus?.is_bound ? 'success' : 'outline'} className="text-xs">
                      {bindingStatus?.is_bound ? '已绑定' : '未绑定'}
                    </Badge>
                  </div>
                  {bindingStatus?.username && (
                    <div className="flex items-center justify-between">
                      <span className="text-primary-100 text-sm">学号</span>
                      <span className="text-sm font-medium">{bindingStatus.username}</span>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-primary-100 text-sm">最近同步</span>
                    <span className="text-sm font-medium flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {lastSyncAt ? new Date(lastSyncAt).toLocaleString('zh-CN') : '未同步'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 科目类型分布 */}
            {scores.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">科目分布</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(() => {
                    const colors = ['bg-primary-500', 'bg-secondary-500', 'bg-emerald-500', 'bg-orange-500', 'bg-purple-500'];
                    return courseDistribution.map(([type, count], idx) => (
                      <div key={type} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className={`w-3 h-3 rounded-full ${colors[idx % colors.length]}`} />
                          <span className="text-sm text-surface-700 dark:text-surface-300">{type}</span>
                        </div>
                        <span className="text-sm font-medium text-surface-900 dark:text-surface-100">{count} 门</span>
                      </div>
                    ));
                  })()}
                </div>
              </CardContent>
            </Card>
            )}

            {/* 薄弱科目 */}
            {scores.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-red-500" />
                  薄弱科目
                </CardTitle>
                <CardDescription>分数最低的科目，建议重点关注</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {weakSubjects.map((item, idx) => {
                    const num = parseScore(item.score);
                    return (
                      <div key={idx} className="flex items-center justify-between">
                        <span className="text-sm text-surface-700 dark:text-surface-300 truncate flex-1 mr-2">
                          {idx + 1}. {item.name}
                        </span>
                        <Badge
                          variant={!isNaN(num) && num >= 70 ? 'warning' : 'destructive'}
                          className="text-xs font-bold"
                        >
                          {item.score ?? item.level ?? '-'}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
};
