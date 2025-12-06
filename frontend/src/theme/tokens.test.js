import { describe, it, expect } from 'vitest';
import {
  getStatusToken,
  getPriorityToken,
  getSeverityToken,
  STATUS_OPTIONS,
  STATUS_FLOW,
} from './tokens';

describe('tokens', () => {
  it('provides fallback tokens for unknown status', () => {
    expect(getStatusToken('unknown')).toBe(getStatusToken('todo'));
  });

  it('keeps status options and flow in sync', () => {
    const optionValues = STATUS_OPTIONS.map((o) => o.value);
    expect(optionValues).toContain('blocked');
    expect(STATUS_FLOW).toEqual(['todo', 'in_progress', 'done']);
  });

  it('maps priority aliases and falls back to low', () => {
    expect(getPriorityToken('later')).toBe(getPriorityToken('low'));
    expect(getPriorityToken('mvp')).toBe(getPriorityToken('high'));
    expect(getPriorityToken('release1')).toBe(getPriorityToken('medium'));
    expect(getPriorityToken(undefined)).toBe(getPriorityToken('low'));
  });

  it('falls back severity to medium when missing', () => {
    expect(getSeverityToken(undefined)).toBe(getSeverityToken('medium'));
    expect(getSeverityToken('unknown')).toBe(getSeverityToken('medium'));
  });
});

