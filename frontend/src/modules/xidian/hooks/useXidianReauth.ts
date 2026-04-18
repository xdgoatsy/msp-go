import { createContext, useContext } from 'react';

export interface XidianReauthContextValue {
  triggerReauth: () => Promise<void>;
}

export const XidianReauthContext = createContext<XidianReauthContextValue | null>(null);

export const useXidianReauth = () => {
  const context = useContext(XidianReauthContext);
  if (!context) {
    throw new Error('useXidianReauth must be used within XidianReauthProvider');
  }
  return context;
};
