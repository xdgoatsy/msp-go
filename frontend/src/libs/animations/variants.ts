import { type Variants } from 'framer-motion';
import { springConfig, transitionConfig, animationDuration } from './config';

/**
 * Framer Motion 动画预设
 *
 * 设计原则：
 * - DRY: 统一的动画变体，避免在组件中重复定义
 * - 可复用: 可以在任何使用 Framer Motion 的组件中使用
 * - 一致性: 确保整个应用的动画效果保持一致
 */

/**
 * 淡入淡出动画
 */
export const fadeVariants: Variants = {
  hidden: {
    opacity: 0,
  },
  visible: {
    opacity: 1,
    transition: transitionConfig.default,
  },
  exit: {
    opacity: 0,
    transition: transitionConfig.fast,
  },
};

/**
 * 向上滑入动画
 */
export const slideUpVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 20,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: springConfig.gentle,
  },
  exit: {
    opacity: 0,
    y: -20,
    transition: transitionConfig.fast,
  },
};

/**
 * 向下滑入动画
 */
export const slideDownVariants: Variants = {
  hidden: {
    opacity: 0,
    y: -20,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: springConfig.gentle,
  },
  exit: {
    opacity: 0,
    y: 20,
    transition: transitionConfig.fast,
  },
};

/**
 * 向左滑入动画
 */
export const slideLeftVariants: Variants = {
  hidden: {
    opacity: 0,
    x: 20,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: springConfig.gentle,
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: transitionConfig.fast,
  },
};

/**
 * 向右滑入动画
 */
export const slideRightVariants: Variants = {
  hidden: {
    opacity: 0,
    x: -20,
  },
  visible: {
    opacity: 1,
    x: 0,
    transition: springConfig.gentle,
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: transitionConfig.fast,
  },
};

/**
 * 缩放动画
 */
export const scaleVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
  },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springConfig.snappy,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: transitionConfig.fast,
  },
};

/**
 * 弹跳缩放动画
 */
export const bounceScaleVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.8,
  },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springConfig.bouncy,
  },
  exit: {
    opacity: 0,
    scale: 0.8,
    transition: transitionConfig.fast,
  },
};

/**
 * 旋转淡入动画
 */
export const rotateVariants: Variants = {
  hidden: {
    opacity: 0,
    rotate: -10,
  },
  visible: {
    opacity: 1,
    rotate: 0,
    transition: springConfig.gentle,
  },
  exit: {
    opacity: 0,
    rotate: 10,
    transition: transitionConfig.fast,
  },
};

/**
 * 模态框动画（背景 + 内容）
 */
export const modalVariants = {
  backdrop: {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
    exit: { opacity: 0 },
  },
  content: {
    hidden: {
      opacity: 0,
      scale: 0.95,
      y: 20,
    },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: springConfig.snappy,
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      y: 20,
      transition: transitionConfig.fast,
    },
  },
};

/**
 * Toast 通知动画
 */
export const toastVariants: Variants = {
  hidden: {
    opacity: 0,
    x: 100,
    scale: 0.95,
  },
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: springConfig.snappy,
  },
  exit: {
    opacity: 0,
    x: 100,
    scale: 0.95,
    transition: transitionConfig.fast,
  },
};

/**
 * 列表项交错动画
 */
export const staggerContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.05,
    },
  },
};

export const staggerItemVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 20,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: springConfig.gentle,
  },
};

/**
 * 悬停动画
 */
export const hoverVariants: Variants = {
  rest: {
    scale: 1,
  },
  hover: {
    scale: 1.05,
    transition: springConfig.snappy,
  },
  tap: {
    scale: 0.95,
    transition: springConfig.snappy,
  },
};

/**
 * 按钮点击动画
 */
export const buttonVariants: Variants = {
  rest: {
    scale: 1,
  },
  hover: {
    scale: 1.02,
    transition: springConfig.snappy,
  },
  tap: {
    scale: 0.98,
    transition: springConfig.snappy,
  },
};

/**
 * 卡片悬停动画
 */
export const cardHoverVariants: Variants = {
  rest: {
    y: 0,
    boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  },
  hover: {
    y: -4,
    boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    transition: springConfig.snappy,
  },
};

/**
 * 页面过渡动画
 */
export const pageVariants: Variants = {
  initial: {
    opacity: 0,
    y: 20,
  },
  enter: {
    opacity: 1,
    y: 0,
    transition: {
      duration: animationDuration.normal / 1000,
      ease: [0.4, 0, 0.2, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -20,
    transition: {
      duration: animationDuration.fast / 1000,
      ease: [0.4, 0, 1, 1],
    },
  },
};

/**
 * 抽屉动画（从右侧滑入）
 */
export const drawerVariants: Variants = {
  hidden: {
    x: '100%',
  },
  visible: {
    x: 0,
    transition: springConfig.snappy,
  },
  exit: {
    x: '100%',
    transition: transitionConfig.fast,
  },
};

/**
 * 下拉菜单动画
 */
export const dropdownVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: -10,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springConfig.snappy,
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -10,
    transition: transitionConfig.fast,
  },
};

/**
 * 工具提示动画
 */
export const tooltipVariants: Variants = {
  hidden: {
    opacity: 0,
    scale: 0.9,
  },
  visible: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 0.15,
      ease: [0, 0, 0.2, 1],
    },
  },
  exit: {
    opacity: 0,
    scale: 0.9,
    transition: {
      duration: 0.1,
      ease: [0.4, 0, 1, 1],
    },
  },
};

/**
 * 导航项激活指示器动画（下划线滑动）
 */
export const navIndicatorVariants: Variants = {
  inactive: {
    scaleX: 0,
    opacity: 0,
    transition: {
      duration: 0.2,
      ease: [0.4, 0, 1, 1], // easeIn
    },
  },
  active: {
    scaleX: 1,
    opacity: 1,
    transition: {
      duration: 0.25,
      ease: [0.4, 0, 0.2, 1], // easeInOut
    },
  },
};

/**
 * 优化的页面过渡动画（更微妙的位移 + 更快的时序）
 */
export const pageTransitionVariants: Variants = {
  initial: {
    opacity: 0,
    y: 8, // 比 pageVariants 的 20px 更微妙
  },
  enter: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: [0, 0, 0.2, 1], // easeOut
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: 0.15, // 退出更快
      ease: [0.4, 0, 1, 1], // easeIn
    },
  },
};
