/**
 * System Resource Governor & Performance Throttler.
 * Single Responsibility: Monitors system RAM & CPU load to keep >= 3GB RAM free and >= 20% CPU free.
 */
import * as os from 'os';
import { config } from '../config';

export interface SystemResourceStatus {
  freeRamBytes: number;
  freeRamGb: number;
  totalRamGb: number;
  cpuUsagePercent: number;
  cpuFreePercent: number;
  isRamSufficient: boolean;
  isCpuSufficient: boolean;
}

export class SystemGovernor {
  private static instance: SystemGovernor;

  private constructor() {}

  public static getInstance(): SystemGovernor {
    if (!SystemGovernor.instance) {
      SystemGovernor.instance = new SystemGovernor();
    }
    return SystemGovernor.instance;
  }

  /**
   * Get current RAM and CPU metrics.
   */
  public getStatus(): SystemResourceStatus {
    const freeRamBytes = os.freemem();
    const totalRamBytes = os.totalmem();
    const freeRamGb = freeRamBytes / (1024 * 1024 * 1024);
    const totalRamGb = totalRamBytes / (1024 * 1024 * 1024);

    // Approximate CPU load
    const cpus = os.cpus();
    let totalIdle = 0;
    let totalTick = 0;
    for (const cpu of cpus) {
      for (const type in cpu.times) {
        totalTick += (cpu.times as any)[type];
      }
      totalIdle += cpu.times.idle;
    }
    const idlePercent = totalTick > 0 ? (totalIdle / totalTick) * 100 : 50;
    const cpuUsagePercent = Math.max(0, Math.min(100, 100 - idlePercent));
    const cpuFreePercent = 100 - cpuUsagePercent;

    const isRamSufficient = freeRamBytes >= config.minFreeRamBytes;
    const isCpuSufficient = cpuUsagePercent <= config.maxCpuPercent;

    return {
      freeRamBytes,
      freeRamGb,
      totalRamGb,
      cpuUsagePercent,
      cpuFreePercent,
      isRamSufficient,
      isCpuSufficient
    };
  }

  /**
   * Pause/sleep until system RAM is >= 3GB and CPU usage <= 80%.
   */
  public async ensureResourceAvailability(maxWaitMs = 15000): Promise<boolean> {
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitMs) {
      const status = this.getStatus();
      if (status.isRamSufficient && status.isCpuSufficient) {
        return true;
      }

      console.warn(
        `   ⚠️ [Resource Governor Throttling] RAM Free: ${status.freeRamGb.toFixed(2)} GB (Req ≥ ${(config.minFreeRamBytes / (1024*1024*1024)).toFixed(1)} GB) | ` +
        `CPU Free: ${status.cpuFreePercent.toFixed(1)}% (Req ≥ ${(100 - config.maxCpuPercent).toFixed(0)}%). Waiting 1s...`
      );

      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return false;
  }
}
