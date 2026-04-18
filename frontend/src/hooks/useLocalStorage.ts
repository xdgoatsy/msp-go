import { useState } from 'react';
import { logger } from '../libs/utils/logger';

const storageLogger = logger.createContextLogger('LocalStorage');

/**
 * LocalStorage Hook
 * @param key 存储键名
 * @param initialValue 初始值
 * @returns [存储的值, 设置值的函数, 删除值的函数]
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void, () => void] {
  // 从 localStorage 读取初始值
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      storageLogger.error(`Error reading localStorage key "${key}"`, error);
      return initialValue;
    }
  });

  // 设置值到 state 和 localStorage
  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
      storageLogger.debug(`Set localStorage key "${key}"`);
    } catch (error) {
      storageLogger.error(`Error setting localStorage key "${key}"`, error);
    }
  };

  // 删除值
  const removeValue = () => {
    try {
      window.localStorage.removeItem(key);
      setStoredValue(initialValue);
      storageLogger.debug(`Removed localStorage key "${key}"`);
    } catch (error) {
      storageLogger.error(`Error removing localStorage key "${key}"`, error);
    }
  };

  return [storedValue, setValue, removeValue];
}
