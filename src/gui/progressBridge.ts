/**
 * Background Processing Progress Raylib GUI Bridge.
 * Spawns python/gui/progress_gui.py and pipes progress data via stdin.
 */
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { config } from '../config';

export interface ProgressUpdate {
  current_file?: string;
  queue_length?: number;
  status?: string;
  progress_percent?: number;
}

export class ProgressBridge {
  private static instance: ProgressBridge | null = null;
  private proc: ChildProcess | null = null;

  private constructor() {}

  public static getInstance(): ProgressBridge {
    if (!ProgressBridge.instance) {
      ProgressBridge.instance = new ProgressBridge();
    }
    return ProgressBridge.instance;
  }

  public ensureRunning(): void {
    if (this.proc && !this.proc.killed && this.proc.exitCode === null) return;

    const guiScript = path.join(config.pythonDir, 'gui', 'progress_gui.py');
    this.proc = spawn(config.pythonBin, ['-u', guiScript], {
      cwd: config.projectRoot,
      windowsHide: false,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    if (this.proc.stdout) {
      this.proc.stdout.on('data', (data: Buffer) => {
        const text = data.toString('utf-8').trim();
        if (text && !text.includes('INFO:') && !text.includes('RAYLIB STATIC') && !text.includes('WARNING:')) {
          console.log('   [Progress GUI]', text);
        }
      });
    }

    if (this.proc.stderr) {
      this.proc.stderr.on('data', (data: Buffer) => {
        const err = data.toString('utf-8').trim();
        if (err && !err.includes('INFO:') && !err.includes('RAYLIB STATIC') && !err.includes('WARNING:')) {
          console.warn('   ⚠️ Progress GUI notice:', err);
        }
      });
    }

    this.proc.on('error', (err) => {
      console.error('Failed to start Progress GUI:', err);
      this.proc = null;
    });

    this.proc.on('close', () => {
      this.proc = null;
    });
  }

  public update(data: ProgressUpdate): void {
    this.ensureRunning();
    if (this.proc && this.proc.stdin && !this.proc.stdin.destroyed) {
      try {
        const payload = { type: 'update', ...data };
        this.proc.stdin.write(JSON.stringify(payload) + '\n');
      } catch (e) {
        console.error('Failed to send progress update:', e);
      }
    }
  }

  public stop(): void {
    if (this.proc && this.proc.stdin && !this.proc.stdin.destroyed) {
      try {
        this.proc.stdin.write(JSON.stringify({ type: 'exit' }) + '\n');
      } catch (e) {}
    }
    this.proc = null;
  }
}
