import { Link } from 'react-router-dom';
import { Home, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/Button';

/**
 * 404 页面
 *
 * 当用户访问不存在的路由时显示
 */
export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 flex items-center justify-center px-6">
      <div className="max-w-md w-full text-center">
        {/* 404 大标题 */}
        <div className="mb-8">
          <h1 className="text-9xl font-bold text-blue-600 dark:text-blue-400 mb-4">
            404
          </h1>
          <div className="h-1 w-32 bg-gradient-to-r from-blue-600 to-purple-600 mx-auto rounded-full" />
        </div>

        {/* 错误信息 */}
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          页面未找到
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          抱歉，您访问的页面不存在或已被移除。
          <br />
          请检查 URL 是否正确，或返回首页继续浏览。
        </p>

        {/* 操作按钮 */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/">
            <Button variant="primary" size="lg" className="w-full sm:w-auto">
              <Home className="w-5 h-5 mr-2" />
              返回首页
            </Button>
          </Link>
          <Button
            variant="outline"
            size="lg"
            onClick={() => window.history.back()}
            className="w-full sm:w-auto"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回上一页
          </Button>
        </div>

        {/* 装饰性元素 */}
        <div className="mt-12 text-gray-400 dark:text-gray-600">
          <p className="text-sm">
            如果您认为这是一个错误，请联系技术支持
          </p>
        </div>
      </div>
    </div>
  );
};
