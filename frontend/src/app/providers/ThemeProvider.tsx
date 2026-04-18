import { useEffect } from 'react';
import { useAppSelector } from '@/store';
import { selectTheme } from '@/store/slices/uiSlice';

/**
 * 主题应用组件
 * 根据 Redux store 中的主题状态动态切换深色/浅色模式
 */
export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useAppSelector(selectTheme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return <>{children}</>;
};
