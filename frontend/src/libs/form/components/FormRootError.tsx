import React from 'react';
import { AlertCircle } from 'lucide-react';
import { formErrorStyles } from '../../styles/formStyles';

interface FormRootErrorProps {
  /** 错误信息 */
  message?: string;
}

/**
 * 表单级别错误提示组件
 *
 * @description 用于显示表单级别的错误信息（如登录失败、注册失败等）
 * 遵循 DRY 原则，从 LoginForm 和 RegisterForm 中提取的公共组件
 *
 * @example
 * ```tsx
 * {errors.root && <FormRootError message={errors.root.message} />}
 * ```
 */
export const FormRootError: React.FC<FormRootErrorProps> = ({ message }) => {
  if (!message) return null;

  return (
    <div className={formErrorStyles.container}>
      <AlertCircle className={formErrorStyles.icon} />
      <span>{message}</span>
    </div>
  );
};
