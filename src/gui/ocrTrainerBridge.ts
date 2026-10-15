/**
 * OCR Trainer Raylib GUI Bridge.
 * Single Responsibility: Spawns and communicates with python/gui/ocr_trainer_gui.py
 * Supports persistent interactive sessions (single window across all documents)
 * and single-file reviews.
 */
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { config } from '../config';

export interface OcrTrainerResult {
  action: 'confirmed' | 'skipped' | 'exit_session' | 'error';
  rating?: number; // 1 to 5 stars
  docType?: string;
  docTypeName?: string;
  fields?: {
    name?: string;
    dob?: string;
    age?: string;
    aadhaar?: string;
    address?: string;
    prev_cert_no?: string;
    years_in_goa?: string;
    [key: string]: string | undefined;
  };
  spellCorrection?: {
    original: string;
    corrected: string;
  };
  message?: string;
}

export interface OcrTrainerParams {
  filePath: string;
  docType: string;
  docTypeName: string;
  confidence?: number;
  extractedFields?: Record<string, string | number>;
  rawOcrLines?: string[];
  docIndex?: number;
  totalDocs?: number;
}

/**
 * Persistent GUI Session manager that keeps a single Raylib window open
 * across multiple documents, eliminating window destruction and recreation.
 */
export class OcrTrainerSession {
  private proc: ChildProcess | null = null;
  private pendingResolver: ((result: OcrTrainerResult) => void) | null = null;
  private stdoutBuffer: string = '';
  private isAlive: boolean = false;

  public async start(): Promise<void> {
    const guiScript = path.join(config.pythonDir, 'gui', 'ocr_trainer_gui.py');
    const args = [guiScript, '--session'];

    return new Promise((resolve, reject) => {
      this.proc = spawn(config.pythonBin, args, {
        cwd: config.projectRoot,
        windowsHide: false,
        stdio: ['pipe', 'pipe', 'pipe']
      });

      this.isAlive = true;

      this.proc.stdout?.on('data', (data: Buffer) => {
        const text = data.toString('utf-8');
        this.stdoutBuffer += text;

        const lines = this.stdoutBuffer.split('\n');
        this.stdoutBuffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.includes('JSON_RESULT:')) {
            const jsonStr = trimmed.substring(trimmed.indexOf('JSON_RESULT:') + 12).trim();
            try {
              const res = JSON.parse(jsonStr) as OcrTrainerResult;
              if (this.pendingResolver) {
                const resolver = this.pendingResolver;
                this.pendingResolver = null;
                resolver(res);
              }
            } catch (e) {
              console.error('Failed to parse OCR Trainer GUI result JSON:', e);
            }
          }
        }
      });

      this.proc.stderr?.on('data', (data: Buffer) => {
        const err = data.toString('utf-8').trim();
        if (!err.includes('INFO:') && !err.includes('RAYLIB STATIC') && err.length > 0) {
          console.error(`[Trainer GUI] ${err}`);
        }
      });

      this.proc.on('close', (code: number) => {
        this.isAlive = false;
        if (this.pendingResolver) {
          const resolver = this.pendingResolver;
          this.pendingResolver = null;
          resolver({ action: 'exit_session', message: `Window closed with code ${code}` });
        }
      });

      this.proc.on('error', (err: Error) => {
        this.isAlive = false;
        if (this.pendingResolver) {
          const resolver = this.pendingResolver;
          this.pendingResolver = null;
          resolver({ action: 'error', message: err.message });
        }
        reject(err);
      });

      // Window starts asynchronously
      resolve();
    });
  }

  public async reviewDocument(params: OcrTrainerParams): Promise<OcrTrainerResult> {
    if (!this.isAlive || !this.proc || !this.proc.stdin) {
      return { action: 'exit_session', message: 'Trainer GUI session is not active' };
    }

    if (!fs.existsSync(params.filePath)) {
      return { action: 'error', message: `File not found: ${params.filePath}` };
    }

    return new Promise((resolve) => {
      this.pendingResolver = resolve;
      const payload = {
        command: 'load_doc',
        filePath: params.filePath,
        docType: params.docType,
        docTypeName: params.docTypeName,
        confidence: params.confidence ?? 0.9,
        extractedFields: params.extractedFields ?? {},
        rawOcrLines: params.rawOcrLines ?? [],
        docIndex: params.docIndex ?? 1,
        totalDocs: params.totalDocs ?? 1
      };
      this.proc?.stdin?.write(JSON.stringify(payload) + '\n');
    });
  }

  public async close(): Promise<void> {
    if (this.isAlive && this.proc && this.proc.stdin) {
      try {
        this.proc.stdin.write(JSON.stringify({ command: 'close' }) + '\n');
        this.proc.stdin.end();
      } catch {}
    }
  }
}

/**
 * Spawns the Raylib OCR Trainer GUI window for human rating & field ground-truth verification.
 */
export async function requestOcrTrainingReview(params: OcrTrainerParams): Promise<OcrTrainerResult> {
  const session = new OcrTrainerSession();
  await session.start();
  const res = await session.reviewDocument(params);
  await session.close();
  return res;
}
