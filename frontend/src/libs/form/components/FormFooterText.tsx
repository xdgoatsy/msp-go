import React from 'react';
import { linkStyles } from '../../styles/formStyles';

interface FormFooterTextProps {
  /** 显示的文字 */
  children: React.ReactNode;
}

/**
 * 表单底部文字组件
 *
 * @description 用于表单底部的说明文字，如"登录即表示您同意我们的服务条款"
 * 遵循 DRY 原则，从 LoginForm 和 RegisterForm 中提取的公共组件
 *
 * @example
 * ```tsx
 * <FormFooterText>
 *   登录即表示您同意我们的服务条款和隐私政策
 * </FormFooterText>
 * ```
 */
export const FormFooterText: React.FC<FormFooterTextProps> = ({ children }) => {
  return <p className={linkStyles.footer}>{children}</p>;
};
