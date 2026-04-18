/**
 * 自定义 Hooks 统一导出
 *
 * Hooks 放置规范：
 * - 通用/跨功能 hooks → src/hooks/（本目录）
 *   适用于不依赖特定业务逻辑的通用 hooks，如 useDebounce、useLocalStorage
 *
 * - 功能域专属 hooks → modules/xxx/hooks/
 *   适用于封装特定业务模块逻辑的 hooks，如 modules/auth/hooks/useAuth
 *
 * - 页面专属 hooks → pages/xxx/hooks/
 *   适用于仅被单个页面使用的 hooks，如 pages/student/SessionChatPage/hooks/useChatStream
 */

export { useDebounce } from './useDebounce';
export { useLocalStorage } from './useLocalStorage';

