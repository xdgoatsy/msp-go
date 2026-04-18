import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { submitButtonStyles } from '../../styles/formStyles';

interface FormSubmitButtonProps {
  /** 按钮文字 */
  children: React.ReactNode;
  /** 是否加载中 */
  isLoading?: boolean;
  /** 是否禁用 */
  disabled?: boolean;
  /** 是否显示箭头图标 */
  showArrow?: boolean;
}

/**
 * 表单提交按钮组件
 *
 * @description 统一的表单提交按钮样式
 * 遵循 DRY 原则，从 LoginForm 和 RegisterForm 中提取的公共组件
 *
 * @example
 * ```tsx
 * <FormSubmitButton isLoading={isSubmitting}>
 *   登录
 * </FormSubmitButton>
 * ```
 */
export const FormSubmitButton: React.FC<FormSubmitButtonProps> = ({
  children,
  isLoading = false,
  disabled = false,
  showArrow = true,
}) => {
  return (
    <Button
      type="submit"
      className={submitButtonStyles.primary}
      isLoading={isLoading}
      disabled={disabled}
    >
      <span className={submitButtonStyles.content}>
        {children}
        {showArrow && <ArrowRight className={submitButtonStyles.arrow} />}
      </span>
    </Button>
  );
};
