import React from 'react';
import { dividerStyles } from '../../styles/formStyles';

interface FormDividerProps {
  /** 分隔线中间的文字 */
  text?: string;
}

/**
 * 表单分隔线组件
 *
 * @description 用于表单中的分隔线，通常显示"或"等文字
 * 遵循 DRY 原则，从 LoginForm 和 RegisterForm 中提取的公共组件
 *
 * @example
 * ```tsx
 * <FormDivider text="或" />
 * ```
 */
export const FormDivider: React.FC<FormDividerProps> = ({ text = '或' }) => {
  return (
    <div className={dividerStyles.container}>
      <div className={dividerStyles.line}>
        <div className={dividerStyles.border}></div>
      </div>
      <div className={dividerStyles.textContainer}>
        <span className={dividerStyles.text}>{text}</span>
      </div>
    </div>
  );
};
