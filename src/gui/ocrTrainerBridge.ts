/**
 * OCR Trainer Raylib GUI Bridge.
 * Single Responsibility: Spawns python/gui/ocr_trainer_gui.py and parses interactive user rating & field verification.
 */
import { spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { config } from '../config';

export interface OcrTrainerResult {
  action: 'confirmed' | 'skipped' | 'error';
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
}

/**
 * Spawns the Raylib OCR Trainer GUI window for human rating & field ground-truth verification.
 */
export async function requestOcrTrainingReview(params: OcrTrainerParams): Promise<OcrTrainerResult> {
  if (!fs.existsSync(params.filePath)) {
    return {
      action: 'error',
      message: `File not found: ${params.filePath}`
    };
  }

  const guiScript = path.join(config.pythonDir, 'gui', 'ocr_trainer_gui.py');
  const args = [
    guiScript,
    '--file', params.filePath,
    '--type', params.docType,
    '--name', params.docTypeName,
    '--confidence', String(params.confidence || 0.9),
    '--fields', JSON.stringify(params.extractedFields || {}),
    '--ocr-lines', JSON.stringify(params.rawOcrLines || [])
  ];

  return new Promise((resolve) => {
    let resultJSON: OcrTrainerResult | null = null;
    const proc = spawn(config.pythonBin, args, {
      cwd: config.projectRoot,
      windowsHide: false
    });

    proc.stdout.on('data', (data: Buffer) => {
      const output = data.toString('utf-8');
      const lines = output.split('\n');
      for (const line of lines) {
        if (line.includes('JSON_RESULT:')) {
          const jsonStr = line.substring(line.indexOf('JSON_RESULT:') + 12).trim();
          try {
            resultJSON = JSON.parse(jsonStr) as OcrTrainerResult;
          } catch (e) {
            console.error('Failed to parse OCR Trainer GUI result JSON:', e);
          }
        }
      }
    });

    proc.stderr.on('data', (data: Buffer) => {
      const err = data.toString('utf-8').trim();
      // Suppress standard Raylib window initialization logs from polluting console
      if (!err.includes('INFO:') && !err.includes('RAYLIB STATIC') && err.length > 0) {
        console.error(`[Trainer GUI] ${err}`);
      }
    });

    proc.on('close', (code: number) => {
      if (resultJSON) {
        resolve(resultJSON);
      } else {
        resolve({
          action: 'skipped',
          docType: params.docType,
          docTypeName: params.docTypeName,
          message: `GUI closed with code ${code}`
        });
      }
    });

    proc.on('error', (err: Error) => {
      resolve({
        action: 'error',
        docType: params.docType,
        docTypeName: params.docTypeName,
        message: err.message
      });
    });
  });
}
