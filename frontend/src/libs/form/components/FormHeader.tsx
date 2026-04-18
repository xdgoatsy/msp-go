import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { formHeaderStyles } from '../../styles/formStyles';

interface FormHeaderProps {
  /** 标题 */
  title: string;
  /** 副标题 */
  subtitle: string;
  /** 图标组件 */
  icon: LucideIcon;
}

/**
 * 表单头部组件
 *
 * @description 用于表单顶部的标题区域，包含图标、标题和副标题
 * 遵循 DRY 原则，从 LoginForm 和 RegisterForm 中提取的公共组件
 *
 * @example
 * ```tsx
 * <FormHeader
 *   icon={Sparkles}
 *   title="欢迎回来"
 *   subtitle="登录后开启智能数学学习之旅"
 * />
 * ```
 */
export const FormHeader: React.FC<FormHeaderProps> = ({ title, subtitle, icon: Icon }) => {
  return (
    <div className={formHeaderStyles.container}>
      <div className={formHeaderStyles.iconContainer}>
        <Icon className={formHeaderStyles.icon} />
      </div>
      <h1 className={formHeaderStyles.title}>{title}</h1>
      <p className={formHeaderStyles.subtitle}>{subtitle}</p>
    </div>
  );
};
