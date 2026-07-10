import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ExercisePanel, useExerciseViewModel } from '@/modules/exercise';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { MainLayout } from '../../components/layout/MainLayout';
import { MessageCircle, Sparkles } from 'lucide-react';

export const ExercisePage: React.FC = () => {
  const navigate = useNavigate();

  // 状态提升：在父组件调用 hook，以便侧边栏按钮访问题目数据
  const exerciseVM = useExerciseViewModel();
  const { currentQuestion } = exerciseVM;

  // 呼叫 AI 导师
  const handleCallAITutor = () => {
    if (!currentQuestion) {
      navigate('/session/new');
      return;
    }

    const knowledgePoints = currentQuestion.knowledgePoints?.length
      ? currentQuestion.knowledgePoints.join('、')
      : '未标注';

    const initialMessage = [
      '请帮我分析这道题：',
      '',
      `**分组: ${currentQuestion.title || '未分类'}**`,
      '',
      currentQuestion.content,
      '',
      `难度：${Math.round(currentQuestion.difficulty * 100)}%  |  类型：${currentQuestion.type}`,
      `知识点：${knowledgePoints}`,
      '',
      '请帮我理解解题思路。',
    ].join('\n');

    navigate('/session/new', { state: { initialMessage } });
  };

  return (
    <MainLayout>
      <div className="container mx-auto p-6 max-w-6xl">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* 主练习区域 */}
          <div className="lg:col-span-8 space-y-6">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100 tracking-tight">
                智能刷题
              </h1>
            </div>

            <ExercisePanel {...exerciseVM} />
          </div>

          {/* 侧边栏 */}
          <div className="lg:col-span-4 space-y-6">
            <Card className="border-primary-200 dark:border-primary-800 bg-linear-to-br from-primary-50 to-purple-50 dark:from-primary-950/50 dark:to-purple-950/50">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary-500" />
                  学习工具
                </CardTitle>
              </CardHeader>
              <CardContent>
                <button
                  onClick={handleCallAITutor}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-linear-to-r from-primary-600 to-purple-600 hover:from-primary-700 hover:to-purple-700 text-white font-medium shadow-lg hover:shadow-xl transition-all duration-300 group"
                >
                  <MessageCircle className="h-5 w-5 group-hover:scale-110 transition-transform duration-300" />
                  呼叫 AI 导师
                  <Sparkles className="h-4 w-4 opacity-75 group-hover:opacity-100 transition-opacity duration-300" />
                </button>
                <p className="text-xs text-center text-surface-500 dark:text-surface-400 mt-3">
                  {currentQuestion
                    ? '点击向 AI 导师请教当前题目'
                    : '点击开始与 AI 导师对话'}
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};
