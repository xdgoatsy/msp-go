import React from 'react';
import { linkStyles } from '../../styles/formStyles';

interface FormFooterLinkProps {
  /** 提示文字 */
  text: string;
  /** 链接文字 */
  linkText: string;
  /** 点击回调 */
  onClick?: () => void;
}

/**
 * 表单底部链接组件
 *
 * @description 用于表单底部的切换链接，如"还没有账号？立即注册"
 * 遵循 DRY 原则，从 LoginForm 和 RegisterForm 中提取的公共组件
 *
 * @example
 * ```tsx
 * <FormFooterLink
 *   text="还没有账号？"
 *   linkText="立即注册"
 *   onClick={onSwitchToRegister}
 * />
 * ```
 */
export const FormFooterLink: React.FC<FormFooterLinkProps> = ({
  text,
  linkText,
  onClick,
}) => {
  return (
    <div className="text-center">
      <p className={linkStyles.helper}>
        {text}{' '}
        <button
          type="button"
          className={linkStyles.primary}
          onClick={onClick}
        >
          {linkText}
        </button>
      </p>
    </div>
  );
};
