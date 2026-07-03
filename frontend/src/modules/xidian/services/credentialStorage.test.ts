import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearCredential, hasCredential, loadCredential, saveCredential } from './credentialStorage';

const CREDENTIAL_KEY = 'xidian_cred';

describe('credentialStorage legacy cleanup', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('clears legacy localStorage credentials without persisting new values', () => {
    localStorage.setItem(CREDENTIAL_KEY, 'legacy');

    saveCredential('student', 'password');

    expect(localStorage.getItem(CREDENTIAL_KEY)).toBeNull();
    expect(loadCredential()).toBeNull();
    expect(hasCredential()).toBe(false);
  });

  it('does not throw when browser storage blocks cleanup', () => {
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('storage blocked');
    });

    expect(() => clearCredential()).not.toThrow();
    expect(() => saveCredential('student', 'password')).not.toThrow();
    expect(loadCredential()).toBeNull();
    expect(hasCredential()).toBe(false);
  });
});
