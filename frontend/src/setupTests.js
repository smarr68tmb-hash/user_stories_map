import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock localStorage with default implementation
const localStorageMock = {
  getItem: vi.fn((key) => null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
};

vi.stubGlobal('localStorage', localStorageMock);

