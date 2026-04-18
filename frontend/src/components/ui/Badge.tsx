import * as React from 'react';
import { cn } from '../../libs/utils/cn';
import { animationCombos } from '../../libs/animations';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'outline';
}

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
          animationCombos.buttonHover,
          {
            'bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-300':
              variant === 'default',
            'bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300':
              variant === 'secondary',
            'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-300':
              variant === 'success',
            'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300':
              variant === 'warning',
            'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300':
              variant === 'destructive',
            'border border-surface-200 text-surface-700 dark:border-surface-700 dark:text-surface-300':
              variant === 'outline',
          },
          className
        )}
        {...props}
      />
    );
  }
);
Badge.displayName = 'Badge';

export { Badge };
