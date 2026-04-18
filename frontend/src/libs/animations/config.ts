/**
 * 动画配置文件
 *
 * 设计原则：
 * - KISS: 简单的配置对象，易于使用
 * - DRY: 统一的动画参数，避免在组件中重复定义
 * - 一致性: 确保整个应用的动画效果保持一致
 */

/**
 * 动画持续时间（毫秒）
 */
export const animationDuration = {
  /** 极快 - 用于微交互 */
  fastest: 100,
  /** 快速 - 用于简单过渡 */
  fast: 200,
  /** 正常 - 默认动画速度 */
  normal: 300,
  /** 慢速 - 用于复杂动画 */
  slow: 500,
  /** 极慢 - 用于特殊效果 */
  slowest: 700,
} as const;

/**
 * 缓动函数
 *
 * 基于 CSS easing functions 和 Framer Motion 的标准缓动
 */
export const animationEasing = {
  /** 线性 - 匀速运动 */
  linear: 'linear',
  /** 缓入 - 慢速开始 */
  easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
  /** 缓出 - 慢速结束 */
  easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
  /** 缓入缓出 - 慢速开始和结束 */
  easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  /** 弹性 - 带有弹性效果 */
  spring: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  /** 平滑 - 非常平滑的过渡 */
  smooth: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
} as const;

/**
 * 动画延迟（毫秒）
 */
export const animationDelay = {
  /** 无延迟 */
  none: 0,
  /** 短延迟 */
  short: 100,
  /** 中等延迟 */
  medium: 200,
  /** 长延迟 */
  long: 300,
} as const;

/**
 * 常用动画预设
 *
 * 这些预设可以直接在 Tailwind 类名中使用
 */
export const animationPresets = {
  /** 淡入 */
  fadeIn: {
    duration: animationDuration.normal,
    easing: animationEasing.easeOut,
  },
  /** 淡出 */
  fadeOut: {
    duration: animationDuration.normal,
    easing: animationEasing.easeIn,
  },
  /** 向上滑入 */
  slideUp: {
    duration: animationDuration.normal,
    easing: animationEasing.easeOut,
  },
  /** 向下滑入 */
  slideDown: {
    duration: animationDuration.normal,
    easing: animationEasing.easeOut,
  },
  /** 向左滑入 */
  slideLeft: {
    duration: animationDuration.normal,
    easing: animationEasing.easeOut,
  },
  /** 向右滑入 */
  slideRight: {
    duration: animationDuration.normal,
    easing: animationEasing.easeOut,
  },
  /** 缩放进入 */
  scaleIn: {
    duration: animationDuration.normal,
    easing: animationEasing.spring,
  },
  /** 缩放退出 */
  scaleOut: {
    duration: animationDuration.fast,
    easing: animationEasing.easeIn,
  },
  /** 旋转 */
  spin: {
    duration: 1000,
    easing: animationEasing.linear,
  },
  /** 脉冲 */
  pulse: {
    duration: 2000,
    easing: animationEasing.easeInOut,
  },
  /** 弹跳 */
  bounce: {
    duration: animationDuration.slow,
    easing: animationEasing.spring,
  },
  /** 摇晃 */
  shake: {
    duration: animationDuration.slow,
    easing: animationEasing.easeInOut,
  },
} as const;

/**
 * Framer Motion 专用的弹簧配置
 */
export const springConfig = {
  /** 柔和弹簧 - 适合大多数 UI 动画 */
  gentle: {
    type: 'spring' as const,
    stiffness: 300,
    damping: 30,
  },
  /** 快速弹簧 - 适合快速响应 */
  snappy: {
    type: 'spring' as const,
    stiffness: 400,
    damping: 25,
  },
  /** 缓慢弹簧 - 适合大型元素 */
  slow: {
    type: 'spring' as const,
    stiffness: 200,
    damping: 35,
  },
  /** 弹性弹簧 - 带有明显的弹性效果 */
  bouncy: {
    type: 'spring' as const,
    stiffness: 500,
    damping: 20,
  },
  /** 僵硬弹簧 - 几乎没有弹性 */
  stiff: {
    type: 'spring' as const,
    stiffness: 600,
    damping: 40,
  },
} as const;

/**
 * 过渡配置
 */
export const transitionConfig = {
  /** 默认过渡 */
  default: {
    duration: animationDuration.normal / 1000, // Framer Motion 使用秒
    ease: [0.4, 0, 0.2, 1], // easeInOut
  },
  /** 快速过渡 */
  fast: {
    duration: animationDuration.fast / 1000,
    ease: [0, 0, 0.2, 1], // easeOut
  },
  /** 慢速过渡 */
  slow: {
    duration: animationDuration.slow / 1000,
    ease: [0.4, 0, 0.2, 1], // easeInOut
  },
} as const;

/**
 * 动画变体类型
 */
export type AnimationVariant = keyof typeof animationPresets;
export type SpringVariant = keyof typeof springConfig;
export type TransitionVariant = keyof typeof transitionConfig;
