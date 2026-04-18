import * as React from 'react';
import { cn } from '../../libs/utils/cn';

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  variant?: 'default' | 'success' | 'warning' | 'destructive';
  size?: 'sm' | 'default' | 'lg';
  showLabel?: boolean;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, max = 100, variant = 'default', size = 'default', showLabel = false, ...props }, ref) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

    return (
      <div className={cn('w-full', className)} {...props}>
        <div
          ref={ref}
          className={cn(
            'relative w-full overflow-hidden rounded-full bg-surface-100 dark:bg-surface-800',
            {
              'h-1.5': size === 'sm',
              'h-2.5': size === 'default',
              'h-4': size === 'lg',
            }
          )}
        >
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500 ease-out',
              {
                'bg-primary-600 dark:bg-primary-500': variant === 'default',
                'bg-emerald-600 dark:bg-emerald-500': variant === 'success',
                'bg-yellow-600 dark:bg-yellow-500': variant === 'warning',
                'bg-red-600 dark:bg-red-500': variant === 'destructive',
              }
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
        {showLabel && (
          <div className="mt-1 flex justify-between text-xs text-surface-500 dark:text-surface-400">
            <span>{value}</span>
            <span>{percentage.toFixed(0)}%</span>
          </div>
        )}
      </div>
    );
  }
);
Progress.displayName = 'Progress';

export { Progress };
