/**
 * Applicant Photo Upload Processing Pipeline.
 * Single Responsibility: Orchestrates AI background removal (RTX 4060 CUDA) and C fast JPEG compression under 50KB.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { spawnSync } from 'child_process';
import { config } from '../config';
import { compressImageWithNativeEngine } from './nativeProcessor';

export interface ProcessImageOptions {
  maxKB?: number;
  useAI?: boolean;
  model?: string;
  width?: number;
  height?: number;
  outputPath?: string;
}

export async function processPhotoForUpload(
  inputPath: string,
  options: ProcessImageOptions = {}
): Promise<string> {
  const maxKB = options.maxKB ?? 50;
  const useAI = options.useAI ?? true;
  const model = options.model ?? 'u2net_human_seg';

  const absInputPath = path.resolve(inputPath);
  if (!fs.existsSync(absInputPath)) {
    throw new Error(`Input photo file not found at: ${absInputPath}`);
  }

  const ext = path.extname(absInputPath);
  const baseName = path.basename(absInputPath, ext);
  const dirName = path.dirname(absInputPath);

  const tempAiOutput = path.join(os.tmpdir(), `ai_temp_${Date.now()}_${baseName}.png`);
  const finalOutput = options.outputPath ? path.resolve(options.outputPath) : path.join(dirName, `${baseName}_processed.jpg`);

  let currentInput = absInputPath;
  let skipCbg = false;

  // Step 1: AI Background Removal with RTX 4060 CUDA
  if (useAI) {
    console.log(`[Photo Processor] Running AI Background Removal (${model})...`);
    const aiScriptPath = path.join(config.pythonDir, 'vision', 'ai_remove_bg.py');
    const pyResult = spawnSync(config.pythonBin, [
      '-E',
      aiScriptPath,
      absInputPath,
      tempAiOutput,
      '--model', model
    ], {
      cwd: config.projectRoot,
      encoding: 'utf-8',
      env: {
        ...process.env,
        PYTHONPATH: undefined,
        PYTHONHOME: undefined,
      }
    });

    if (pyResult.status === 0 && fs.existsSync(tempAiOutput)) {
      currentInput = tempAiOutput;
      skipCbg = true;
      console.log(`[Photo Processor] AI segmentation complete -> ${tempAiOutput}`);
    } else {
      console.warn(`[Photo Processor] AI script notice (${pyResult.stderr || pyResult.stdout}). Falling back to C flood-fill...`);
    }
  }

  // Step 2: C Engine Resizing & Iterative JPEG Compression
  console.log(`[Photo Processor] Resizing & compressing to max ${maxKB} KB...`);
  compressImageWithNativeEngine(currentInput, finalOutput, {
    maxKB,
    width: options.width,
    height: options.height,
    skipBgRemove: skipCbg
  });

  // Clean up temp AI output
  if (fs.existsSync(tempAiOutput)) {
    try {
      fs.unlinkSync(tempAiOutput);
    } catch {}
  }

  const finalStats = fs.statSync(finalOutput);
  console.log(`[Photo Processor] Success! Saved output to ${finalOutput} (${(finalStats.size / 1024).toFixed(1)} KB)`);

  return finalOutput;
}
