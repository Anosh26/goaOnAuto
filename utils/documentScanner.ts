import { createWorker } from 'tesseract.js';
import * as path from 'path';
import * as fs from 'fs';
import { execSync } from 'child_process';
import { classifyDocumentText, ClassificationResult } from './documentClassifier';

export interface ScanOptions {
  autoRename?: boolean;
  targetDir?: string;
  workerLang?: string;
}

/**
 * Tries Python GPU OCR engine (EasyOCR / PyTorch CUDA) first.
 * If GPU/Python is unavailable, falls back to CPU WASM (Tesseract.js).
 */
function tryPythonGpuCpuOcr(imagePath: string): { text: string; isGpu: boolean; device: string } | null {
  const pyScript = path.resolve(__dirname, 'gpuOcrEngine.py');
  try {
    const output = execSync(`python "${pyScript}" "${imagePath}"`, { stdio: 'pipe' }).toString();
    const parsed = JSON.parse(output);
    if (parsed.text && parsed.text.trim().length > 0) {
      return {
        text: parsed.text,
        isGpu: !!parsed.is_gpu,
        device: parsed.device || 'CPU'
      };
    }
  } catch {}
  return null;
}

export async function processDocumentImage(
  imagePath: string, 
  options: ScanOptions = {}
): Promise<{ classification: ClassificationResult; newPath?: string }> {
  if (!fs.existsSync(imagePath)) {
    throw new Error(`File not found: ${imagePath}`);
  }

  let extractedText = '';
  
  // 1. Try GPU OCR Engine (with Python CPU fallback)
  const pythonOcrResult = tryPythonGpuCpuOcr(imagePath);

  if (pythonOcrResult) {
    extractedText = pythonOcrResult.text;
    if (pythonOcrResult.isGpu) {
      console.log(`   🚀 OCR GPU Accelerated (${pythonOcrResult.device})`);
    } else {
      console.log(`   💻 OCR CPU Engine Active (${pythonOcrResult.device})`);
    }
  } else {
    // 2. Fallback to Tesseract.js CPU WASM worker
    const worker = await createWorker(options.workerLang || 'eng');
    try {
      const { data: { text } } = await worker.recognize(imagePath);
      extractedText = text;
    } finally {
      await worker.terminate();
    }
  }

  const classification = classifyDocumentText(extractedText, path.basename(imagePath), path.dirname(imagePath));

  let newPath: string | undefined = undefined;

  if (options.autoRename) {
    const dir = options.targetDir || path.dirname(imagePath);
    let targetName = classification.suggestedFilename;
    let targetPath = path.join(dir, targetName);
    
    // Ensure unique filename if destination exists
    let counter = 1;
    const ext = path.extname(targetName);
    const stem = path.basename(targetName, ext);

    while (fs.existsSync(targetPath) && targetPath !== imagePath) {
      targetName = `${stem}_${counter}${ext}`;
      targetPath = path.join(dir, targetName);
      counter++;
    }

    fs.renameSync(imagePath, targetPath);
    newPath = targetPath;
  }

  return { classification, newPath };
}
