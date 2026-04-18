# 动画系统使用指南

## 概述

本项目提供了统一的动画系统，包括 Tailwind CSS 动画和 Framer Motion 预设，确保整个应用的动画效果保持一致。

## 设计原则

- **KISS**: 简单易用的 API
- **DRY**: 避免重复定义动画
- **一致性**: 统一的动画参数和效果
- **性能**: 优化的动画配置

---

## 快速开始

### 1. Tailwind CSS 动画

直接在 className 中使用预定义的动画类：

```tsx
// 淡入动画
<div className="animate-fade-in">内容</div>

// 向上滑入
<div className="animate-slide-up">内容</div>

// 缩放进入
<div className="animate-scale-in">内容</div>

// 组合使用
<div className="animate-fade-in animate-slide-up duration-300">
  内容
</div>
```

### 2. Framer Motion 动画

使用预定义的变体：

```tsx
import { motion } from 'framer-motion';
import { fadeVariants, slideUpVariants } from '@/libs/animations';

// 基础用法
<motion.div
  initial="hidden"
  animate="visible"
  exit="exit"
  variants={fadeVariants}
>
  内容
</motion.div>

// 向上滑入
<motion.div variants={slideUpVariants}>
  内容
</motion.div>
```

---

## 可用动画

### Tailwind CSS 动画类

#### 淡入淡出
- `animate-fade-in` - 淡入（300ms）
- `animate-fade-out` - 淡出（200ms）

#### 滑动动画
- `animate-slide-up` - 向上滑入
- `animate-slide-down` - 向下滑入
- `animate-slide-left` - 向左滑入
- `animate-slide-right` - 向右滑入
- `animate-slide-in-right` - 从右侧滑入（Toast 专用）
- `animate-slide-out-right` - 向右侧滑出（Toast 专用）

#### 缩放动画
- `animate-scale-in` - 缩放进入（带弹性）
- `animate-scale-out` - 缩放退出
- `animate-zoom-in` - 放大进入
- `animate-zoom-out` - 缩小退出

#### 旋转动画
- `animate-spin` - 旋转（1s）
- `animate-spin-slow` - 慢速旋转（3s）
- `animate-spin-fast` - 快速旋转（0.5s）

#### 特殊效果
- `animate-pulse` - 脉冲效果
- `animate-bounce` - 弹跳效果
- `animate-shake` - 摇晃效果
- `animate-wiggle` - 摆动效果
- `animate-float` - 漂浮效果
- `animate-gradient-x` - 渐变动画

---

## Framer Motion 变体

### 基础变体

```tsx
import {
  fadeVariants,
  slideUpVariants,
  slideDownVariants,
  slideLeftVariants,
  slideRightVariants,
  scaleVariants,
  bounceScaleVariants,
  rotateVariants,
} from '@/libs/animations';
```

### 组件专用变体

```tsx
import {
  modalVariants,      // 模态框动画
  toastVariants,      // Toast 通知动画
  drawerVariants,     // 抽屉动画
  dropdownVariants,   // 下拉菜单动画
  tooltipVariants,    // 工具提示动画
  pageVariants,       // 页面过渡动画
} from '@/libs/animations';
```

### 交互变体

```tsx
import {
  hoverVariants,      // 悬停动画
  buttonVariants,     // 按钮动画
  cardHoverVariants,  // 卡片悬停动画
} from '@/libs/animations';
```

### 列表动画

```tsx
import {
  staggerContainerVariants,
  staggerItemVariants,
} from '@/libs/animations';

// 使用示例
<motion.ul variants={staggerContainerVariants}>
  {items.map((item) => (
    <motion.li key={item.id} variants={staggerItemVariants}>
      {item.name}
    </motion.li>
  ))}
</motion.ul>
```

---

## 动画配置

### 持续时间

```tsx
import { animationDuration } from '@/libs/animations';

animationDuration.fastest  // 100ms - 微交互
animationDuration.fast     // 200ms - 简单过渡
animationDuration.normal   // 300ms - 默认速度
animationDuration.slow     // 500ms - 复杂动画
animationDuration.slowest  // 700ms - 特殊效果
```

### 缓动函数

```tsx
import { animationEasing } from '@/libs/animations';

animationEasing.linear     // 匀速
animationEasing.easeIn     // 缓入
animationEasing.easeOut    // 缓出
animationEasing.easeInOut  // 缓入缓出
animationEasing.spring     // 弹性
animationEasing.smooth     // 平滑
```

### 弹簧配置

```tsx
import { springConfig } from '@/libs/animations';

springConfig.gentle  // 柔和弹簧（推荐）
springConfig.snappy  // 快速弹簧
springConfig.slow    // 缓慢弹簧
springConfig.bouncy  // 弹性弹簧
springConfig.stiff   // 僵硬弹簧
```

---

## 使用示例

### 示例 1: 模态框动画

```tsx
import { motion, AnimatePresence } from 'framer-motion';
import { modalVariants } from '@/libs/animations';

export const Modal = ({ isOpen, onClose, children }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* 背景 */}
          <motion.div
            variants={modalVariants.backdrop}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
            className="fixed inset-0 bg-black/50"
          />

          {/* 内容 */}
          <motion.div
            variants={modalVariants.content}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed inset-0 flex items-center justify-center"
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
```

### 示例 2: Toast 通知

```tsx
import { motion } from 'framer-motion';
import { toastVariants } from '@/libs/animations';

export const ToastItem = ({ toast }) => {
  return (
    <motion.div
      variants={toastVariants}
      initial="hidden"
      animate="visible"
      exit="exit"
      className="bg-white rounded-lg shadow-lg p-4"
    >
      {toast.message}
    </motion.div>
  );
};
```

### 示例 3: 按钮悬停效果

```tsx
import { motion } from 'framer-motion';
import { buttonVariants } from '@/libs/animations';

export const Button = ({ children, onClick }) => {
  return (
    <motion.button
      variants={buttonVariants}
      initial="rest"
      whileHover="hover"
      whileTap="tap"
      onClick={onClick}
      className="px-4 py-2 bg-primary-600 text-white rounded-lg"
    >
      {children}
    </motion.button>
  );
};
```

### 示例 4: 卡片悬停效果

```tsx
import { motion } from 'framer-motion';
import { cardHoverVariants } from '@/libs/animations';

export const Card = ({ children }) => {
  return (
    <motion.div
      variants={cardHoverVariants}
      initial="rest"
      whileHover="hover"
      className="bg-white rounded-lg p-6"
    >
      {children}
    </motion.div>
  );
};
```

### 示例 5: 列表交错动画

```tsx
import { motion } from 'framer-motion';
import { staggerContainerVariants, staggerItemVariants } from '@/libs/animations';

export const List = ({ items }) => {
  return (
    <motion.ul
      variants={staggerContainerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-2"
    >
      {items.map((item) => (
        <motion.li
          key={item.id}
          variants={staggerItemVariants}
          className="p-4 bg-white rounded-lg"
        >
          {item.name}
        </motion.li>
      ))}
    </motion.ul>
  );
};
```

### 示例 6: 页面过渡

```tsx
import { motion } from 'framer-motion';
import { pageVariants } from '@/libs/animations';

export const Page = ({ children }) => {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="enter"
      exit="exit"
    >
      {children}
    </motion.div>
  );
};
```

---

## 工具函数

### getStaggerDelay

创建交错动画的延迟：

```tsx
import { getStaggerDelay } from '@/libs/animations';

{items.map((item, index) => (
  <motion.div
    key={item.id}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ delay: getStaggerDelay(index, 100) }}
  >
    {item.name}
  </motion.div>
))}
```

### createTransition

创建自定义过渡配置：

```tsx
import { createTransition } from '@/libs/animations';

<motion.div
  animate={{ x: 100 }}
  transition={createTransition(300, 'easeOut')}
/>
```

### createSpring

创建自定义弹簧配置：

```tsx
import { createSpring } from '@/libs/animations';

<motion.div
  animate={{ scale: 1.2 }}
  transition={createSpring(400, 25)}
/>
```

---

## 预设组合

使用预定义的动画组合类：

```tsx
import { animationCombos } from '@/libs/animations';

// 模态框进入
<div className={animationCombos.modalEnter}>内容</div>

// Toast 进入
<div className={animationCombos.toastEnter}>通知</div>

// 页面进入
<div className={animationCombos.pageEnter}>页面内容</div>

// 卡片悬停
<div className={animationCombos.cardHover}>卡片</div>

// 按钮悬停
<button className={animationCombos.buttonHover}>按钮</button>
```

---

## 性能优化建议

1. **使用 `will-change`**: 对于频繁动画的元素，添加 `will-change` 属性
   ```tsx
   <motion.div style={{ willChange: 'transform' }}>
   ```

2. **避免动画布局属性**: 优先使用 `transform` 和 `opacity`，避免动画 `width`、`height` 等

3. **使用 `AnimatePresence`**: 处理组件卸载动画
   ```tsx
   <AnimatePresence mode="wait">
     {isVisible && <Component />}
   </AnimatePresence>
   ```

4. **减少动画复杂度**: 在低性能设备上考虑禁用或简化动画

---

## 最佳实践

1. **保持一致性**: 在整个应用中使用相同的动画参数
2. **适度使用**: 不要过度使用动画，避免分散用户注意力
3. **有意义的动画**: 动画应该增强用户体验，而不是装饰
4. **响应式动画**: 考虑在移动设备上简化或禁用某些动画
5. **可访问性**: 尊重用户的 `prefers-reduced-motion` 设置

```tsx
// 检测用户偏好
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

<motion.div
  animate={prefersReducedMotion ? {} : { x: 100 }}
/>
```

---

## 故障排除

### 动画不生效

1. 检查是否正确导入了动画配置
2. 确认 Tailwind 配置已更新
3. 检查 Framer Motion 是否正确安装

### 动画卡顿

1. 检查是否动画了布局属性（width、height 等）
2. 使用 Chrome DevTools 的 Performance 面板分析
3. 考虑使用 `transform` 和 `opacity` 替代

### 动画不流畅

1. 检查动画持续时间是否过长
2. 尝试使用不同的缓动函数
3. 减少同时进行的动画数量

---

## 参考资源

- [Framer Motion 文档](https://www.framer.com/motion/)
- [Tailwind CSS 动画](https://tailwindcss.com/docs/animation)
- [CSS 缓动函数](https://easings.net/)
