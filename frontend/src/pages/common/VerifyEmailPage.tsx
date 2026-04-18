import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { MainLayout } from '../../components/layout/MainLayout';
import { apiClient } from '@/libs/http/apiClient';

interface VerifyResult {
  success: boolean;
  message: string;
}

const MISSING_TOKEN_RESULT: VerifyResult = {
  success: false,
  message: '缺少验证链接参数',
};

/**
 * 邮箱验证页：用户点击邮件中的确认链接后打开
 * 路径：/auth/verify-email?token=xxx
 */
export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [loading, setLoading] = useState(() => Boolean(token));

  useEffect(() => {
    if (!token) {
      return;
    }

    let active = true;

    const verifyEmail = async () => {
      setLoading(true);
      setResult(null);

      try {
        const response = await apiClient.get<VerifyResult>('/auth/verify-email', { params: { token } });
        if (active) {
          setResult(response.data);
        }
      } catch (err: unknown) {
        if (active) {
          setResult({
            success: false,
            message: (err as { response?: { data?: { message?: string } } }).response?.data?.message ?? '验证失败，请重试或重新申请',
          });
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void verifyEmail();

    return () => {
      active = false;
    };
  }, [token]);

  const displayResult = token ? result : MISSING_TOKEN_RESULT;
  const isLoading = token ? loading : false;

  return (
    <MainLayout>
      <div className="min-h-[60vh] flex flex-col items-center justify-center px-4">
        {isLoading ? (
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin" />
            <p className="text-surface-600 dark:text-surface-400">正在验证邮箱…</p>
          </div>
        ) : displayResult ? (
          <div className="max-w-md w-full text-center space-y-6">
            {displayResult.success ? (
              <>
                <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
                <h1 className="text-xl font-semibold text-surface-900 dark:text-surface-100">
                  邮箱验证成功
                </h1>
                <p className="text-surface-600 dark:text-surface-400">{displayResult.message}</p>
              </>
            ) : (
              <>
                <XCircle className="w-16 h-16 text-red-500 mx-auto" />
                <h1 className="text-xl font-semibold text-surface-900 dark:text-surface-100">
                  验证失败
                </h1>
                <p className="text-surface-600 dark:text-surface-400">{displayResult.message}</p>
              </>
            )}
            <Link
              to="/welcome"
              className="inline-block px-6 py-2 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors"
            >
              返回首页
            </Link>
          </div>
        ) : null}
      </div>
    </MainLayout>
  );
};
