/**
 * Human Confirmation Raylib GUI Bridge.
 * Single Responsibility: Spawns python/gui/confirmation_gui.py and parses interactive user verification results.
 */
import { spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { config } from '../config';

export interface ConfirmationResult {
  action: 'confirmed' | 'changed' | 'skipped' | 'error';
  docType: string;
  docTypeName: string;
  extractedName?: string;
  customKeyword?: string;
  message?: string;
}

export interface ConfirmationParams {
  filePath: string;
  docType: string;
  docTypeName: string;
  extractedName?: string;
  confidence?: number;
}

/**
 * Spawns the Raylib GUI window for human verification of a classified document.
 */
export async function requestHumanConfirmation(params: ConfirmationParams): Promise<ConfirmationResult> {
  if (!config.enableHumanConfirmation) {
    return {
      action: 'confirmed',
      docType: params.docType,
      docTypeName: params.docTypeName,
      extractedName: params.extractedName
    };
  }

  if (!fs.existsSync(params.filePath)) {
    return {
      action: 'error',
      docType: params.docType,
      docTypeName: params.docTypeName,
      message: `File not found: ${params.filePath}`
    };
  }

  const guiScript = path.join(config.pythonDir, 'gui', 'confirmation_gui.py');
  const args = [
    guiScript,
    '--file', params.filePath,
    '--type', params.docType,
    '--name', params.docTypeName,
    '--person', params.extractedName || '',
    '--confidence', String(params.confidence || 0.9)
  ];

  return new Promise((resolve) => {
    let resultJSON: ConfirmationResult | null = null;
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
            resultJSON = JSON.parse(jsonStr) as ConfirmationResult;
          } catch (e) {
            console.error('Failed to parse confirmation GUI result JSON:', e);
          }
        }
      }
    });

    proc.stderr.on('data', (data: Buffer) => {
      const err = data.toString('utf-8').trim();
      if (err && !err.includes('INFO:') && !err.includes('RAYLIB STATIC')) {
        console.warn('   ⚠️ Raylib GUI notice:', err);
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
          extractedName: params.extractedName,
          message: `GUI process exited with code ${code}`
        });
      }
    });

    proc.on('error', (err: Error) => {
      console.error('Failed to launch Raylib Confirmation GUI:', err);
      resolve({
        action: 'skipped',
        docType: params.docType,
        docTypeName: params.docTypeName,
        extractedName: params.extractedName,
        message: err.message
      });
    });
  });
}
