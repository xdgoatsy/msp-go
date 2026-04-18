import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { Card, CardContent } from '../../components/ui/Card';
import { ArrowLeft } from 'lucide-react';

export const TermsOfServicePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950 text-surface-900 dark:text-surface-100">
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        <Button
          variant="ghost"
          className="mb-6 pl-0 hover:bg-transparent hover:text-primary-600 dark:hover:text-primary-400"
          onClick={() => navigate('/')}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          返回主界面
        </Button>

        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-surface-900 dark:text-surface-100">
            高数学习AI大模型服务条款
          </h1>
          <p className="mt-3 text-surface-500 dark:text-surface-400">
            本服务条款仅适用于西安电子科技大学的高数学习AI大模型产品或服务。
          </p>
          <p className="mt-2 text-sm text-surface-400 dark:text-surface-500">最近更新日期：</p>
        </div>

        <Card>
          <CardContent className="p-6 md:p-8">
            <div className="space-y-4 text-sm text-surface-700 dark:text-surface-300 leading-relaxed">
              <p>感谢您使用高数学习AI大模型产品或服务。</p>
              <p>服务条款内容正在完善中，后续将以公告形式更新。</p>
              <p>如有疑问，请通过邮件与我们联系：1954827225@qq.com。</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
