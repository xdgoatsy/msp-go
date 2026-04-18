/**
 * 服务方法工厂
 *
 * 提供统一的服务方法创建工具，消除重复的 try-catch 和日志记录
 */

import { logger } from '../utils/logger';

export interface ServiceMethodConfig<T> {
  /** 服务名称，用于日志记录 */
  serviceName: string;
  /** 方法名称，用于日志记录 */
  methodName: string;
  /** 实际执行的异步函数 */
  execute: () => Promise<T>;
  /** 错误消息前缀 */
  errorMessage?: string;
  /** 是否在成功时记录日志 */
  logSuccess?: boolean;
  /** 自定义错误处理 */
  onError?: (error: unknown) => void;
}

/**
 * 创建服务方法
 *
 * @description 封装通用的 try-catch 和日志记录逻辑
 *
 * @example
 * ```ts
 * export async function getUsers(): Promise<User[]> {
 *   return createServiceMethod({
 *     serviceName: 'userService',
 *     methodName: 'getUsers',
 *     execute: () => apiClient.get<User[]>('/users'),
 *     errorMessage: '获取用户列表失败',
 *   });
 * }
 * ```
 */
export async function createServiceMethod<T>(
  config: ServiceMethodConfig<T>
): Promise<T> {
  const {
    serviceName,
    methodName,
    execute,
    errorMessage,
    logSuccess = false,
    onError,
  } = config;

  const logPrefix = `[${serviceName}.${methodName}]`;

  try {
    const result = await execute();

    if (logSuccess) {
      logger.debug(`${logPrefix} 成功`);
    }

    return result;
  } catch (error) {
    const message = errorMessage || `${methodName} 失败`;
    logger.error(`${logPrefix} ${message}:`, error);

    if (onError) {
      onError(error);
    }

    throw error;
  }
}

/**
 * 创建带重试的服务方法
 *
 * @description 自动重试失败的请求
 */
export async function createRetryableServiceMethod<T>(
  config: ServiceMethodConfig<T> & {
    /** 最大重试次数 */
    maxRetries?: number;
    /** 重试延迟（毫秒） */
    retryDelay?: number;
    /** 是否应该重试的判断函数 */
    shouldRetry?: (error: unknown, attempt: number) => boolean;
  }
): Promise<T> {
  const {
    serviceName,
    methodName,
    execute,
    errorMessage,
    maxRetries = 3,
    retryDelay = 1000,
    shouldRetry = () => true,
  } = config;

  const logPrefix = `[${serviceName}.${methodName}]`;
  let lastError: unknown;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await execute();
    } catch (error) {
      lastError = error;

      if (attempt < maxRetries && shouldRetry(error, attempt)) {
        logger.warn(`${logPrefix} 第 ${attempt} 次尝试失败，${retryDelay}ms 后重试...`);
        await new Promise((resolve) => setTimeout(resolve, retryDelay));
      }
    }
  }

  const message = errorMessage || `${methodName} 失败（已重试 ${maxRetries} 次）`;
  logger.error(`${logPrefix} ${message}:`, lastError);
  throw lastError;
}

/**
 * 批量执行服务方法
 *
 * @description 并行执行多个服务方法，收集结果
 */
export async function batchServiceMethods<T extends Record<string, () => Promise<unknown>>>(
  methods: T
): Promise<{ [K in keyof T]: Awaited<ReturnType<T[K]>> | null }> {
  const keys = Object.keys(methods) as (keyof T)[];
  const promises = keys.map((key) =>
    methods[key]().catch((error) => {
      logger.error(`[batchServiceMethods] ${String(key)} 失败:`, error);
      return null;
    })
  );

  const results = await Promise.all(promises);

  return keys.reduce(
    (acc, key, index) => {
      acc[key] = results[index] as Awaited<ReturnType<T[typeof key]>> | null;
      return acc;
    },
    {} as { [K in keyof T]: Awaited<ReturnType<T[K]>> | null }
  );
}
