/**
 * 动画工具函数和导出
 *
 * 统一导出所有动画相关的配置和预设
 */

// 导出配置
export * from './config';

// 导出 Framer Motion 变体
export * from './variants';

/**
 * 动画工具函数
 */

/**
 * 创建交错动画的延迟
 *
 * @param index - 元素索引
 * @param baseDelay - 基础延迟（毫秒）
 * @returns 延迟时间（秒）
 *
 * @example
 * ```tsx
 * <motion.div
 *   initial={{ opacity: 0 }}
 *   animate={{ opacity: 1 }}
 *   transition={{ delay: getStaggerDelay(index, 100) }}
 * />
 * ```
 */
export const getStaggerDelay = (index: number, baseDelay: number = 100): number => {
  return (index * baseDelay) / 1000;
};

/**
 * 创建自定义过渡配置
 *
 * @param duration - 持续时间（毫秒）
 * @param easing - 缓动函数
 * @returns Framer Motion 过渡配置
 *
 * @example
 * ```tsx
 * <motion.div
 *   animate={{ x: 100 }}
 *   transition={createTransition(300, 'easeOut')}
 * />
 * ```
 */
export const createTransition = (
  duration: number,
  easing: string | number[] = [0.4, 0, 0.2, 1]
) => {
  return {
    duration: duration / 1000,
    ease: typeof easing === 'string' ? easing : easing,
  };
};

/**
 * 创建弹簧过渡配置
 *
 * @param stiffness - 刚度
 * @param damping - 阻尼
 * @returns Framer Motion 弹簧配置
 *
 * @example
 * ```tsx
 * <motion.div
 *   animate={{ scale: 1.2 }}
 *   transition={createSpring(400, 25)}
 * />
 * ```
 */
export const createSpring = (stiffness: number = 300, damping: number = 30) => {
  return {
    type: 'spring' as const,
    stiffness,
    damping,
  };
};

/**
 * 获取 Tailwind 动画类名
 *
 * @param animation - 动画名称
 * @param duration - 持续时间（可选）
 * @returns Tailwind 类名字符串
 *
 * @example
 * ```tsx
 * <div className={getAnimationClass('fade-in', 'duration-300')}>
 *   内容
 * </div>
 * ```
 */
export const getAnimationClass = (
  animation: string,
  duration?: string
): string => {
  const classes = [`animate-${animation}`];
  if (duration) {
    classes.push(duration);
  }
  return classes.join(' ');
};

/**
 * 预设的动画组合
 */
export const animationCombos = {
  /** 模态框进入动画 */
  modalEnter: 'animate-fade-in animate-scale-in duration-300',
  /** 模态框退出动画 */
  modalExit: 'animate-fade-out animate-scale-out duration-200',
  /** Toast 进入动画 */
  toastEnter: 'animate-slide-in-right duration-300',
  /** Toast 退出动画 */
  toastExit: 'animate-slide-out-right duration-200',
  /** 页面进入动画 */
  pageEnter: 'animate-fade-in animate-slide-up duration-500',
  /** 卡片悬停动画 */
  cardHover: 'transition-all duration-300 hover:shadow-lg hover:-translate-y-1',
  /** 按钮悬停动画 */
  buttonHover: 'transition-colors duration-200',
  /** 输入框聚焦动画 */
  inputFocus: 'transition-all duration-200 focus:ring-2',
  /** 导航项过渡（增强版：颜色+位移+阴影） */
  navItemHover: 'transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-sm',
} as const;
