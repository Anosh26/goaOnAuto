import { createWorker } from 'tesseract.js';
import * as path from 'path';
import * as fs from 'fs';
import { classifyDocumentText, ClassificationResult } from './documentClassifier';

export interface ScanOptions {
  autoRename?: boolean;
  targetDir?: string;
  workerLang?: string;
}

export async function processDocumentImage(
  imagePath: string, 
  options: ScanOptions = {}
): Promise<{ classification: ClassificationResult; newPath?: string }> {
  if (!fs.existsSync(imagePath)) {
    throw new Error(`File not found: ${imagePath}`);
  }

  const worker = await createWorker(options.workerLang || 'eng');
  
  try {
    const { data: { text } } = await worker.recognize(imagePath);
    const classification = classifyDocumentText(text, path.basename(imagePath), path.dirname(imagePath));

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
  } finally {
    await worker.terminate();
  }
}
