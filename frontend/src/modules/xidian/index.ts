/**
 * Xidian 模块 - 西电集成
 */

// Components
export { XidianReauthProvider } from './components/XidianReauthProvider';

// Hooks
export { useXidianReauth } from './hooks/useXidianReauth';

// Services
export { saveCredential, loadCredential, clearCredential, hasCredential } from './services/credentialStorage';
export type { XidianCredential } from './services/credentialStorage';
export { XIDIAN_REAUTH_EVENT, emitXidianReauth } from '@/libs/auth/xidianEvents';
export { default as xidianService } from './services/xidianService';
