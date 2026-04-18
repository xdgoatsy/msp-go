import { describe, expect, it } from 'vitest';
import { getInitialResourceSearch } from '@/libs/utils/resourceUtils';

describe('ResourcesPage URL search params', () => {
  it('initializes resource search from the search query param', () => {
    expect(getInitialResourceSearch('?search=%E6%B4%9B%E5%BF%85%E8%BE%BE%E6%B3%95%E5%88%99')).toBe(
      '洛必达法则'
    );
  });

  it('trims empty search params', () => {
    expect(getInitialResourceSearch('?search=%20%20')).toBe('');
  });
});
