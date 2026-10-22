import { vi, describe, it, expect } from 'vitest';

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
    })),
  },
}));

describe('ApiClient - basic tests', () => {
  it('vitest setup works', () => {
    expect(true).toBe(true);
  });
});