import React from 'react';
import { useAppDispatch, useAppSelector } from '../../store';
import { Sun, Moon } from 'lucide-react';
import { toggleTheme, selectTheme } from '@/store/slices/uiSlice';
import { cn } from '../../libs/utils/cn';
import { animationCombos } from '../../libs/animations';

interface ThemeToggleProps {
  className?: string;
  variant?: 'default' | 'ghost';
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  className,
  variant = 'default'
}) => {
  const dispatch = useAppDispatch();
  const theme = useAppSelector(selectTheme);
  const isDark = theme === 'dark';

  const handleToggle = () => {
    dispatch(toggleTheme());
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      className={cn(
        "relative inline-flex items-center justify-center rounded-lg p-2",
        animationCombos.buttonHover,
        variant === 'default' && [
          "bg-surface-100 hover:bg-surface-200",
          "dark:bg-surface-800 dark:hover:bg-surface-700"
        ],
        variant === 'ghost' && [
          "hover:bg-surface-100",
          "dark:hover:bg-surface-800"
        ],
        "text-surface-600 dark:text-surface-400",
        "hover:text-surface-900 dark:hover:text-surface-100",
        "focus:outline-none focus:ring-2 focus:ring-primary-500/50",
        className
      )}
      aria-label={isDark ? '切换到亮色模式' : '切换到暗色模式'}
      title={isDark ? '切换到亮色模式' : '切换到暗色模式'}
    >
      <div className="relative w-5 h-5">
        <Sun
          className={cn(
            "absolute inset-0 w-5 h-5 transition-all duration-300",
            isDark
              ? "opacity-0 rotate-90 scale-0"
              : "opacity-100 rotate-0 scale-100"
          )}
        />
        <Moon
          className={cn(
            "absolute inset-0 w-5 h-5 transition-all duration-300",
            isDark
              ? "opacity-100 rotate-0 scale-100"
              : "opacity-0 -rotate-90 scale-0"
          )}
        />
      </div>
    </button>
  );
};
