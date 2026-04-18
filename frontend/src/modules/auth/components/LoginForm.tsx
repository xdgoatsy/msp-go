import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAppDispatch } from '@/store';
import { useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { authService } from '@/modules/auth/services/authService';
import { setCredentials } from '@/modules/auth/store/authSlice';
import { loginSchema, type LoginFormData } from '@/libs/validation';
import { User, Lock, Sparkles, GraduationCap, BookOpen } from 'lucide-react';
import { logger } from '@/libs/utils/logger';
import {
  FormField,
  FormHeader,
  FormDivider,
  FormFooterLink,
  FormFooterText,
  FormRootError,
  FormSubmitButton,
  RoleSelector,
  type RoleOption,
} from '@/libs/form';
import { ForgotPasswordModal } from './ForgotPasswordModal';

const authLogger = logger.createContextLogger('Auth');

type UserRole = 'student' | 'teacher';

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister?: () => void;
}

/**
 * 角色选项配置
 */
const roleOptions: RoleOption<UserRole>[] = [
  {
    value: 'student',
    label: '学生',
    description: '进入学习中心',
    icon: GraduationCap,
    gradient: 'from-primary-500 to-secondary-500',
    bgGradient: 'from-primary-50 to-secondary-50 dark:from-primary-900/50 dark:to-secondary-900/50',
    borderColor: 'border-primary-500 dark:border-primary-400',
    textColor: 'text-primary-600 dark:text-primary-400',
  },
  {
    value: 'teacher',
    label: '教师',
    description: '进入教学管理',
    icon: BookOpen,
    gradient: 'from-emerald-500 to-teal-500',
    bgGradient: 'from-emerald-50 to-teal-50 dark:from-emerald-900/50 dark:to-teal-900/50',
    borderColor: 'border-emerald-500 dark:border-emerald-400',
    textColor: 'text-emerald-600 dark:text-emerald-400',
  },
];

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess, onSwitchToRegister }) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [showForgotPassword, setShowForgotPassword] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
      role: 'student',
    },
  });

  // 使用 useWatch 替代 watch()，与 React Compiler 兼容
  const role = useWatch({ control, name: 'role' });

  const onSubmit = async (data: LoginFormData) => {
    try {
      const response = await authService.login({
        username: data.username,
        password: data.password,
        role: data.role,
      });

      // 入口与身份一致：管理员不能在此入口登录，老师/学生不能交叉登录
      const selectedRole = data.role;
      const actualRole = response.user.role;
      if (actualRole === 'admin') {
        setError('root', {
          type: 'manual',
          message: '管理员请使用管理员专用入口登录',
        });
        return;
      }
      if (selectedRole === 'student' && actualRole === 'teacher') {
        setError('root', {
          type: 'manual',
          message: '您已注册为教师，请选择「教师」身份或使用教师入口登录',
        });
        return;
      }
      if (selectedRole === 'teacher' && actualRole === 'student') {
        setError('root', {
          type: 'manual',
          message: '您已注册为学生，请选择「学生」身份或使用学生入口登录',
        });
        return;
      }

      dispatch(setCredentials({
        token: response.token,
        user: response.user,
      }));

      authLogger.info('Login successful', {
        userId: response.user.id,
        role: response.user.role
      });

      if (onSuccess) {
        onSuccess();
      }

      // Navigate based on role
      if (response.user.role === 'teacher') {
        navigate('/teacher/dashboard');
      } else {
        navigate('/course/overview');
      }
    } catch (err) {
      authLogger.security('Login failed', {
        username: data.username,
        role: data.role,
        error: err instanceof Error ? err.message : 'Unknown error'
      });
      setError('root', {
        type: 'manual',
        message: '登录失败，请检查用户名和密码',
      });
    }
  };

  return (
    <div className="w-full space-y-6">
      <FormHeader
        icon={Sparkles}
        title="欢迎回来"
        subtitle="登录后开启智能数学学习之旅"
      />

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <RoleSelector
          options={roleOptions}
          value={role}
          onChange={(value) => setValue('role', value)}
          label="选择身份"
          error={errors.role?.message}
        />

        <FormField
          label="用户名"
          icon={User}
          placeholder="请输入用户名"
          autoComplete="username"
          disabled={isSubmitting}
          error={errors.username?.message}
          {...register('username')}
        />

        <FormField
          label="密码"
          icon={Lock}
          type="password"
          placeholder="请输入密码"
          autoComplete="current-password"
          disabled={isSubmitting}
          error={errors.password?.message}
          {...register('password')}
        />

        <div className="flex justify-end -mt-1">
          <button
            type="button"
            onClick={() => setShowForgotPassword(true)}
            className="text-sm text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 transition-colors"
          >
            忘记密码？
          </button>
        </div>

        <FormRootError message={errors.root?.message} />

        <FormSubmitButton isLoading={isSubmitting}>
          {role === 'student' ? '学生登录' : '教师登录'}
        </FormSubmitButton>
      </form>

      <FormDivider />

      <FormFooterLink
        text="还没有账号？"
        linkText="立即注册"
        onClick={onSwitchToRegister}
      />

      <FormFooterText>
        登录即表示您同意我们的
        <Link
          to="/terms-of-service"
          className="ml-1 text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 underline underline-offset-2"
        >
          服务条款
        </Link>
        和
        <Link
          to="/privacy-policy"
          className="ml-1 text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 underline underline-offset-2"
        >
          隐私政策
        </Link>
      </FormFooterText>

      <ForgotPasswordModal
        isOpen={showForgotPassword}
        onClose={() => setShowForgotPassword(false)}
      />
    </div>
  );
};
