import React from 'react';
import { Card, CardContent } from './Card';
import { ArrowUpRight } from 'lucide-react';
import { cn } from '../../libs/utils/cn';
import { animationCombos } from '../../libs/animations';

/**
 * StatCard 组件属性接口
 *
 * 设计原则：
 * - KISS: 简单的统计卡片，只展示核心信息
 * - DRY: 统一两个页面中的重复实现
 */
interface StatCardProps {
  /** 统计项标题 */
  title: string;
  /** 统计数值 */
  value: string;
  /** 图标元素 */
  icon: React.ReactNode;
  /** 趋势变化文本（可选，如 "+12%"、"-2%"） */
  trend?: string;
  /** 趋势方向，true 为上升（绿色），false 为下降（红色），默认 true */
  trendUp?: boolean;
  /** 自定义类名 */
  className?: string;
}

/**
 * StatCard - 统计卡片组件
 *
 * 用于展示关键统计指标，支持趋势显示
 *
 * @example
 * ```tsx
 * <StatCard
 *   title="今日学习时长"
 *   value="45 分钟"
 *   icon={<Clock className="w-6 h-6 text-blue-500" />}
 *   trend="+12%"
 *   trendUp={true}
 * />
 * ```
 */
export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  trend,
  trendUp = true,
  className
}) => {
  return (
    <Card className={cn(animationCombos.cardHover, className)}>
      <CardContent className="p-6">
        <div className="flex justify-between items-start mb-4">
          {/* 图标容器 */}
          <div className="p-2 bg-surface-50 dark:bg-surface-800 rounded-lg border border-surface-100 dark:border-surface-700">
            {icon}
          </div>

          {/* 趋势标签 */}
          {trend && (
            <div
              className={cn(
                "flex items-center text-xs font-medium px-2 py-1 rounded-full",
                trendUp
                  ? "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30"
                  : "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30"
              )}
            >
              {trend}
              <ArrowUpRight className={cn("w-3 h-3 ml-0.5", !trendUp && "rotate-90")} />
            </div>
          )}
        </div>

        {/* 数值和标题 */}
        <div className="space-y-1">
          <div className="text-2xl md:text-3xl font-bold text-surface-900 dark:text-surface-100">
            {value}
          </div>
          <div className="text-sm text-surface-500 dark:text-surface-400">
            {title}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
