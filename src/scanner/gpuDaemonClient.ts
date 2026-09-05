/**
 * GPU Worker Daemon IPC Client.
 * Single Responsibility: Manages persistent child process lifecycle & JSON-RPC communication with Python GPU worker.
 */
import * as path from 'path';
import { spawn, ChildProcess } from 'child_process';
import { config } from '../config';

export interface AadhaarQrResult {
  success: boolean;
  format?: string;
  name?: string;
  dob?: string;
  gender?: string;
  address?: string;
  [key: string]: any;
}

export interface DaemonItemResult {
  path: string;
  text: string;
  engine: string;
  is_gpu: boolean;
  device: string;
  is_photo: boolean;
  photo_confidence: number;
  photo_reason?: string;
  is_signature: boolean;
  signature_confidence: number;
  signature_ink?: string;
  signature_reason?: string;
}

export interface DaemonResponse {
  id?: number | string;
  success?: boolean;
  is_gpu?: boolean;
  device?: string;
  results?: DaemonItemResult[];
  result?: DaemonItemResult;
  error?: string;
}

export class GpuDaemonClient {
  private static instance: GpuDaemonClient | null = null;
  private process: ChildProcess | null = null;
  private reqCounter = 0;
  private pendingRequests = new Map<number, { resolve: (val: any) => void; reject: (err: any) => void }>();
  private buffer = '';
  private isReady = false;
  private readyPromise: Promise<void> | null = null;

  public static getInstance(): GpuDaemonClient {
    if (!GpuDaemonClient.instance) {
      GpuDaemonClient.instance = new GpuDaemonClient();
    }
    return GpuDaemonClient.instance;
  }

  private constructor() {
    this.ensureProcess();
  }

  private ensureProcess(): Promise<void> {
    if (this.process && !this.process.killed && this.isReady) {
      return Promise.resolve();
    }

    if (this.readyPromise) {
      return this.readyPromise;
    }

    this.readyPromise = new Promise((resolve) => {
      const daemonScript = path.join(config.pythonDir, 'daemons', 'gpu_worker_daemon.py');
      this.process = spawn(config.pythonBin, ['-E', daemonScript], {
        cwd: config.projectRoot,
        stdio: ['pipe', 'pipe', 'inherit'],
        env: {
          ...process.env,
          PYTHONPATH: undefined,
          PYTHONHOME: undefined,
        },
      });

      this.process.stdout?.on('data', (chunk: Buffer) => {
        this.buffer += chunk.toString();
        const lines = this.buffer.split('\n');
        this.buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const data: DaemonResponse = JSON.parse(trimmed);
            if (!this.isReady && (data as any).status === 'ready') {
              this.isReady = true;
              console.log(`   🚀 GPU Worker Daemon Ready: ${(data as any).device} (${(data as any).engine})`);
              resolve();
              continue;
            }

            if (data.id !== undefined && this.pendingRequests.has(Number(data.id))) {
              const { resolve: reqResolve } = this.pendingRequests.get(Number(data.id))!;
              this.pendingRequests.delete(Number(data.id));
              reqResolve(data);
            }
          } catch (e) {
            // Ignore non-JSON log lines
          }
        }
      });

      this.process.on('error', (err) => {
        console.warn(`[GpuDaemon] Worker process error: ${err.message}`);
        this.cleanup();
        resolve();
      });

      this.process.on('exit', () => {
        this.cleanup();
      });

      setTimeout(() => {
        if (!this.isReady) {
          console.warn(`[GpuDaemon] Daemon startup timed out, continuing...`);
          resolve();
        }
      }, 15000);
    });

    return this.readyPromise;
  }

  private cleanup() {
    this.isReady = false;
    this.readyPromise = null;
    this.process = null;
    for (const [_, pending] of this.pendingRequests) {
      pending.reject(new Error('GPU Daemon process exited.'));
    }
    this.pendingRequests.clear();
  }

  private async executeSingleChunk(imagePaths: string[]): Promise<DaemonResponse | null> {
    await this.ensureProcess();
    if (!this.process || !this.process.stdin || this.process.killed) {
      return null;
    }

    const reqId = ++this.reqCounter;
    const reqPayload = JSON.stringify({
      id: reqId,
      action: 'batch_process',
      paths: imagePaths,
    }) + '\n';

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        if (this.pendingRequests.has(reqId)) {
          this.pendingRequests.delete(reqId);
          resolve(null);
        }
      }, 120000);

      this.pendingRequests.set(reqId, {
        resolve: (val) => {
          clearTimeout(timeout);
          resolve(val);
        },
        reject: () => {
          clearTimeout(timeout);
          resolve(null);
        },
      });

      try {
        this.process?.stdin?.write(reqPayload);
      } catch (err) {
        clearTimeout(timeout);
        this.pendingRequests.delete(reqId);
        resolve(null);
      }
    });
  }

  public async batchProcess(imagePaths: string[]): Promise<DaemonResponse | null> {
    if (imagePaths.length === 0) return { results: [] };

    // Process in chunks of 10 for responsive streaming & stability
    const CHUNK_SIZE = 10;
    const allResults: DaemonItemResult[] = [];
    let isGpu = true;
    let device = 'GPU CUDA';

    for (let i = 0; i < imagePaths.length; i += CHUNK_SIZE) {
      const chunk = imagePaths.slice(i, i + CHUNK_SIZE);
      const chunkRes = await this.executeSingleChunk(chunk);

      if (chunkRes && chunkRes.results) {
        allResults.push(...chunkRes.results);
        if (chunkRes.is_gpu !== undefined) isGpu = chunkRes.is_gpu;
        if (chunkRes.device) device = chunkRes.device;
      } else {
        return null;
      }
    }

    return {
      success: true,
      is_gpu: isGpu,
      device,
      results: allResults
    };
  }

  public async aadhaarQrScan(imagePath: string): Promise<AadhaarQrResult | null> {
    await this.ensureProcess();
    if (!this.process || !this.process.stdin || this.process.killed) {
      return null;
    }

    const reqId = ++this.reqCounter;
    const reqPayload = JSON.stringify({
      id: reqId,
      action: 'aadhaar_qr',
      path: imagePath,
    }) + '\n';

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        if (this.pendingRequests.has(reqId)) {
          this.pendingRequests.delete(reqId);
          resolve(null);
        }
      }, 30000); // QR is fast, but set 30s timeout

      this.pendingRequests.set(reqId, {
        resolve: (val) => {
          clearTimeout(timeout);
          resolve(val?.result ?? null);
        },
        reject: () => {
          clearTimeout(timeout);
          resolve(null);
        },
      });

      try {
        this.process?.stdin?.write(reqPayload);
      } catch (err) {
        clearTimeout(timeout);
        this.pendingRequests.delete(reqId);
        resolve(null);
      }
    });
  }
}
