import * as React from 'react';
import { cn } from '../../libs/utils/cn';
import { Loader2 } from 'lucide-react';
import { animationCombos } from '../../libs/animations';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'default', isLoading, children, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          // Base styles with unified animation
          'inline-flex items-center justify-center rounded-md font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:pointer-events-none disabled:opacity-50 shadow-sm',
          animationCombos.buttonHover,

          // Variants
          {
            'bg-primary-600 text-white hover:bg-primary-700': variant === 'primary',
            'bg-secondary-600 text-white hover:bg-secondary-700': variant === 'secondary',
            'border border-surface-200 bg-white hover:bg-surface-100 text-surface-900 dark:border-surface-700 dark:bg-surface-800 dark:hover:bg-surface-700 dark:text-surface-100': variant === 'outline',
            'hover:bg-surface-100 text-surface-900 shadow-none dark:hover:bg-surface-800 dark:text-surface-100': variant === 'ghost',
            'bg-red-600 text-white hover:bg-red-700': variant === 'destructive',
            'text-primary-600 underline-offset-4 hover:underline shadow-none dark:text-primary-400': variant === 'link',
          },

          // Sizes
          {
            'h-10 px-4 py-2': size === 'default',
            'h-9 rounded-md px-3 text-sm': size === 'sm',
            'h-11 rounded-md px-8': size === 'lg',
            'h-10 w-10': size === 'icon',
          },
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button };