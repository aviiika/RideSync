import { describe, expect, it } from 'vitest';

import { formatDistance, formatHeading, formatPercent, formatSpeed, formatStatus } from './format';

describe('formatDistance', () => {
  it('uses metres below a kilometre, rounded to ten', () => {
    expect(formatDistance(834)).toBe('830 m');
    expect(formatDistance(12)).toBe('10 m');
  });

  it('uses kilometres above one, to one decimal', () => {
    expect(formatDistance(1240)).toBe('1.2 km');
    expect(formatDistance(10_500)).toBe('10.5 km');
  });

  it('refuses to render nonsense', () => {
    expect(formatDistance(Number.NaN)).toBe('—');
    expect(formatDistance(-5)).toBe('—');
  });
});

describe('formatHeading', () => {
  it.each([
    [0, 'N'],
    [90, 'E'],
    [180, 'S'],
    [270, 'W'],
    [45, 'NE'],
  ])('reads %s° as a compass point', (degrees, point) => {
    expect(formatHeading(degrees)).toContain(point);
  });

  it('normalises out-of-range bearings', () => {
    expect(formatHeading(360)).toContain('N');
  });
});

describe('formatSpeed and formatPercent', () => {
  it('rounds speed to whole km/h', () => {
    expect(formatSpeed(27.4)).toBe('27 km/h');
  });

  it('renders a fraction as a percentage', () => {
    expect(formatPercent(0.625)).toBe('63%');
  });
});

describe('formatStatus', () => {
  it('renders known statuses in plain language', () => {
    expect(formatStatus('AT_STOP')).toBe('At stop');
    expect(formatStatus('STALE')).toBe('No recent data');
  });

  it('passes through anything it does not recognise', () => {
    expect(formatStatus('FUTURE_STATUS')).toBe('FUTURE_STATUS');
  });
});
