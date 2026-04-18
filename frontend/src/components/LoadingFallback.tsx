import React from 'react';
import { motion } from 'framer-motion';

/**
 * 加载占位组件 - 用于路由懒加载时的过渡效果
 */
export const LoadingFallback: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-50 dark:bg-surface-950">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="text-center"
      >
        {/* 加载动画 */}
        <div className="relative w-16 h-16 mx-auto mb-4">
          <motion.div
            className="absolute inset-0 rounded-full border-4 border-primary-200 dark:border-primary-800"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary-500 dark:border-t-primary-400"
            animate={{ rotate: 360 }}
            transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
          />
        </div>

        {/* 加载文本 */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-surface-600 dark:text-surface-400 text-sm font-medium"
        >
          加载中...
        </motion.p>
      </motion.div>
    </div>
  );
};

export default LoadingFallback;
