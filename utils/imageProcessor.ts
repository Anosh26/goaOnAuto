import * as fs from 'fs';
import * as path from 'path';
import { spawnSync } from 'child_process';

export interface ProcessImageOptions {
  maxKB?: number;
  useAI?: boolean;
  model?: string;
  width?: number;
  height?: number;
}

/**
 * Processes an applicant photo or document image:
 * 1. Runs Python AI human silhouette background removal (GPU/CPU) if useAI is true.
 * 2. Runs compiled C executable for downscaling & iterative JPEG compression under maxKB limit.
 * 
 * @returns Absolute path to the processed photo ready for portal upload.
 */
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

  const projectRoot = path.resolve(__dirname, '..');
  const binPath = path.join(projectRoot, 'bin', 'process_image.exe');
  const aiScriptPath = path.join(projectRoot, 'src', 'image_processor', 'ai_remove_bg.py');

  const ext = path.extname(absInputPath);
  const baseName = path.basename(absInputPath, ext);
  const dirName = path.dirname(absInputPath);

  const tempAiOutput = path.join(dirName, `ai_temp_${baseName}.png`);
  const finalOutput = path.join(dirName, `${baseName}_processed.jpg`);

  let currentInput = absInputPath;
  let skipCbg = false;

  // Step 1: AI Background Removal
  if (useAI) {
    console.log(`[Photo Processor] Running AI Background Removal (${model})...`);
    const pyResult = spawnSync('python', [aiScriptPath, absInputPath, tempAiOutput, '--model', model], {
      shell: true,
      encoding: 'utf-8',
    });

    if (pyResult.status === 0 && fs.existsSync(tempAiOutput)) {
      currentInput = tempAiOutput;
      skipCbg = true;
      console.log(`[Photo Processor] AI segmentation complete -> ${tempAiOutput}`);
    } else {
      console.warn(`[Photo Processor] AI script notice (${pyResult.stderr}). Falling back to C flood-fill...`);
    }
  }

  // Step 2: C Engine Resizing & Iterative JPEG Compression
  console.log(`[Photo Processor] Resizing & compressing to max ${maxKB} KB...`);
  const cArgs: string[] = ['--max-kb', maxKB.toString()];
  if (skipCbg) {
    cArgs.push('--skip-bg-remove');
  }
  if (options.width) {
    cArgs.push('--width', options.width.toString());
  }
  if (options.height) {
    cArgs.push('--height', options.height.toString());
  }

  cArgs.push(`"${currentInput}"`, `"${finalOutput}"`);

  const cResult = spawnSync(binPath, cArgs, { shell: true, encoding: 'utf-8' });

  // Clean up temp AI output if generated
  if (fs.existsSync(tempAiOutput)) {
    try {
      fs.unlinkSync(tempAiOutput);
    } catch {}
  }

  if (cResult.status !== 0 || !fs.existsSync(finalOutput)) {
    throw new Error(`C Image Processor execution failed: ${cResult.stderr || cResult.stdout}`);
  }

  const finalStats = fs.statSync(finalOutput);
  console.log(`[Photo Processor] Success! Saved output to ${finalOutput} (${(finalStats.size / 1024).toFixed(1)} KB)`);

  return finalOutput;
}
