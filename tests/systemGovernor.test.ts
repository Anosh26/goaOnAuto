/**
 * Unit Test for System Resource Governor & Throttler.
 */
import { describe, test, expect } from 'bun:test';
import { SystemGovernor } from '../src/watcher/systemGovernor';

describe('SystemGovernor Resource Throttler', () => {
  test('should return current system status with RAM and CPU metrics', () => {
    const governor = SystemGovernor.getInstance();
    const status = governor.getStatus();

    console.log('\n=== System Hardware Resource Metrics ===');
    console.log(`Free RAM:  ${status.freeRamGb.toFixed(2)} GB / ${status.totalRamGb.toFixed(2)} GB (Sufficient ≥ 3GB: ${status.isRamSufficient})`);
    console.log(`CPU Free:  ${status.cpuFreePercent.toFixed(1)}% (Sufficient ≥ 20%: ${status.isCpuSufficient})`);

    expect(status.freeRamGb).toBeGreaterThan(0);
    expect(status.cpuFreePercent).toBeGreaterThanOrEqual(0);
    expect(status.cpuFreePercent).toBeLessThanOrEqual(100);
  });

  test('should satisfy resource availability check', async () => {
    const governor = SystemGovernor.getInstance();
    const isAvailable = await governor.ensureResourceAvailability(3000);
    expect(typeof isAvailable).toBe('boolean');
  });
});
