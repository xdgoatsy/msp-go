import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button';
import { Card, CardContent } from '../../components/ui/Card';
import { ArrowLeft, Mail, MapPin, Clock } from 'lucide-react';

export const ContactPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950 text-surface-900 dark:text-surface-100">
      <div className="container mx-auto px-6 py-8 max-w-3xl">
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
            联系我们
          </h1>
          <p className="mt-3 text-surface-500 dark:text-surface-400">
            如有任何问题或建议，欢迎与我们联系
          </p>
        </div>

        <div className="grid gap-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
                  <Mail className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-surface-900 dark:text-surface-100 mb-1">
                    电子邮箱
                  </h3>
                  <p className="text-surface-600 dark:text-surface-400">
                    1954827225@qq.com
                  </p>
                  <p className="text-sm text-surface-500 dark:text-surface-500 mt-1">
                    用于问题反馈、功能建议、合作咨询
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-secondary-100 dark:bg-secondary-900/30 rounded-lg flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-secondary-600 dark:text-secondary-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-surface-900 dark:text-surface-100 mb-1">
                    地址
                  </h3>
                  <p className="text-surface-600 dark:text-surface-400">
                    陕西省西安市雁塔区太白南路2号
                  </p>
                  <p className="text-sm text-surface-500 dark:text-surface-500 mt-1">
                    西安电子科技大学
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-10 h-10 bg-accent-100 dark:bg-accent-900/30 rounded-lg flex items-center justify-center">
                  <Clock className="w-5 h-5 text-accent-600 dark:text-accent-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-surface-900 dark:text-surface-100 mb-1">
                    服务时间
                  </h3>
                  <p className="text-surface-600 dark:text-surface-400">
                    周一至周五 9:00 - 18:00
                  </p>
                  <p className="text-sm text-surface-500 dark:text-surface-500 mt-1">
                    邮件咨询通常在 1-3 个工作日内回复
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="mt-6">
          <CardContent className="p-6 text-center">
            <p className="text-surface-600 dark:text-surface-400 text-sm">
              感谢你对高数智学的关注与支持！
              <br />
              我们会认真对待每一条反馈，持续改进产品体验。
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
