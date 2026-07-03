import { useState } from 'react';
import { logger } from '../libs/utils/logger';

const storageLogger = logger.createContextLogger('LocalStorage');

type StoredValueSetter<T> = (value: T | ((val: T) => T)) => void;

interface UseLocalStorageOptions<T> {
  validate?: (value: unknown) => value is T;
}

function getLocalStorage(): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function removeStoredValue(key: string): void {
  try {
    getLocalStorage()?.removeItem(key);
  } catch {
    // 存储不可用时忽略
  }
}

function readStoredValue<T>(
  key: string,
  initialValue: T,
  options?: UseLocalStorageOptions<T>
): T {
  const storage = getLocalStorage();
  if (!storage) {
    return initialValue;
  }

  try {
    const item = storage.getItem(key);
    if (item === null) {
      return initialValue;
    }

    const parsed: unknown = JSON.parse(item);
    if (options?.validate && !options.validate(parsed)) {
      removeStoredValue(key);
      storageLogger.warn('Ignored invalid localStorage value');
      return initialValue;
    }

    return parsed as T;
  } catch (error) {
    removeStoredValue(key);
    storageLogger.warn('Ignored unreadable localStorage value', error);
    return initialValue;
  }
}

/**
 * LocalStorage Hook
 * @param key 存储键名
 * @param initialValue 初始值
 * @param options 可选运行时校验
 * @returns [存储的值, 设置值的函数, 删除值的函数]
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  options?: UseLocalStorageOptions<T>
): [T, StoredValueSetter<T>, () => void] {
  // 从 localStorage 读取初始值
  const [storedValue, setStoredValue] = useState<T>(() =>
    readStoredValue(key, initialValue, options)
  );

  // 设置值到 state 和 localStorage
  const setValue: StoredValueSetter<T> = (value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      getLocalStorage()?.setItem(key, JSON.stringify(valueToStore));
      storageLogger.debug('Set localStorage value');
    } catch (error) {
      storageLogger.error('Error setting localStorage value', error);
    }
  };

  // 删除值
  const removeValue = () => {
    try {
      getLocalStorage()?.removeItem(key);
      storageLogger.debug('Removed localStorage value');
    } catch (error) {
      storageLogger.error('Error removing localStorage value', error);
    }
    setStoredValue(initialValue);
  };

  return [storedValue, setValue, removeValue];
}
