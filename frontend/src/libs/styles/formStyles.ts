/**
 * 表单样式常量
 *
 * @description 统一管理表单相关的 TailwindCSS 样式类名
 * 遵循 DRY 原则，消除 LoginForm、RegisterForm 等组件中重复的样式定义
 */

/**
 * 输入框基础样式
 */
export const inputStyles = {
  /** 基础输入框样式 */
  base: 'pl-4 pr-4 py-3 bg-surface-50 dark:bg-surface-800 border-surface-200 dark:border-surface-700 rounded-xl focus:bg-white dark:focus:bg-surface-900 focus:border-primary-400 dark:focus:border-primary-500 focus:ring-2 focus:ring-primary-100 dark:focus:ring-primary-900/50 transition-all text-surface-900 dark:text-surface-100 placeholder:text-surface-400 dark:placeholder:text-surface-500',

  /** 错误状态样式 */
  error: 'border-red-500 dark:border-red-500 focus:border-red-500 focus:ring-red-100',
} as const;

/**
 * 标签样式
 */
export const labelStyles = {
  /** 基础标签样式 */
  base: 'text-sm font-medium text-surface-700 dark:text-surface-300',

  /** 带图标的标签样式 */
  withIcon: 'text-sm font-medium text-surface-700 dark:text-surface-300 flex items-center gap-2',

  /** 标签图标样式 */
  icon: 'w-4 h-4 text-surface-400 dark:text-surface-500',
} as const;

/**
 * 角色选择器样式
 */
export const roleSelectorStyles = {
  /** 选择按钮基础样式 */
  button: {
    base: 'relative p-4 rounded-xl border-2 transition-all duration-200 text-left group',
    unselected: 'border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800 hover:border-surface-300 dark:hover:border-surface-600 hover:bg-surface-100 dark:hover:bg-surface-700',
  },

  /** 图标容器样式 */
  iconContainer: {
    base: 'rounded-lg flex items-center justify-center transition-all',
    selected: 'text-white shadow-md',
    unselected: 'bg-surface-200 dark:bg-surface-700 text-surface-500 dark:text-surface-400 group-hover:bg-surface-300 dark:group-hover:bg-surface-600',
  },

  /** 标签文字样式 */
  label: {
    base: 'font-semibold text-sm',
    unselected: 'text-surface-700 dark:text-surface-300',
  },

  /** 描述文字样式 */
  description: 'text-xs text-surface-400 dark:text-surface-500 mt-0.5',

  /** 选中指示器样式 */
  indicator: 'absolute top-2 right-2 w-5 h-5 rounded-full flex items-center justify-center',
} as const;

/**
 * 表单错误提示样式
 */
export const formErrorStyles = {
  /** 错误容器样式 */
  container: 'flex items-center gap-3 p-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-100 dark:border-red-800',

  /** 错误图标样式 */
  icon: 'w-5 h-5 flex-shrink-0',
} as const;

/**
 * 提交按钮样式
 */
export const submitButtonStyles = {
  /** 主要提交按钮样式 */
  primary: 'w-full py-3 rounded-xl bg-gradient-to-r from-primary-500 to-secondary-500 hover:from-primary-600 hover:to-secondary-600 text-white font-medium shadow-lg shadow-primary-500/25 hover:shadow-xl hover:shadow-primary-500/30 transition-all duration-300 group',

  /** 按钮内容容器样式 */
  content: 'flex items-center justify-center gap-2',

  /** 箭头图标样式 */
  arrow: 'w-4 h-4 transition-transform group-hover:translate-x-1',
} as const;

/**
 * 分隔线样式
 */
export const dividerStyles = {
  /** 分隔线容器样式 */
  container: 'relative',

  /** 分隔线样式 */
  line: 'absolute inset-0 flex items-center',

  /** 分隔线本身样式 */
  border: 'w-full border-t border-surface-200 dark:border-surface-700',

  /** 分隔线文字容器样式 */
  textContainer: 'relative flex justify-center text-xs',

  /** 分隔线文字样式 */
  text: 'px-3 bg-white dark:bg-surface-900 text-surface-400 dark:text-surface-500',
} as const;

/**
 * 链接样式
 */
export const linkStyles = {
  /** 主要链接样式 */
  primary: 'font-semibold text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors',

  /** 辅助文字样式 */
  helper: 'text-sm text-surface-500 dark:text-surface-400',

  /** 页脚文字样式 */
  footer: 'text-center text-xs text-surface-400 dark:text-surface-500',
} as const;

/**
 * 表单头部样式
 */
export const formHeaderStyles = {
  /** 头部容器样式 */
  container: 'text-center space-y-3',

  /** 图标容器样式 */
  iconContainer: 'inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-secondary-500 shadow-lg shadow-primary-500/25 mb-2',

  /** 图标样式 */
  icon: 'w-8 h-8 text-white',

  /** 标题样式 */
  title: 'text-2xl font-bold tracking-tight text-surface-900 dark:text-surface-100',

  /** 副标题样式 */
  subtitle: 'text-sm text-surface-500 dark:text-surface-400',
} as const;

/**
 * 角色选项预设配置
 */
export const rolePresets = {
  student: {
    value: 'student' as const,
    label: '学生',
    gradient: 'from-primary-500 to-secondary-500',
    bgGradient: 'from-primary-50 to-secondary-50 dark:from-primary-900/50 dark:to-secondary-900/50',
    borderColor: 'border-primary-500 dark:border-primary-400',
    textColor: 'text-primary-600 dark:text-primary-400',
  },
  teacher: {
    value: 'teacher' as const,
    label: '教师',
    gradient: 'from-emerald-500 to-teal-500',
    bgGradient: 'from-emerald-50 to-teal-50 dark:from-emerald-900/50 dark:to-teal-900/50',
    borderColor: 'border-emerald-500 dark:border-emerald-400',
    textColor: 'text-emerald-600 dark:text-emerald-400',
  },
} as const;

export type RolePresetKey = keyof typeof rolePresets;
