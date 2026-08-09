import { createWorker } from 'tesseract.js';
import * as path from 'path';
import * as fs from 'fs';
import { execSync } from 'child_process';
import { classifyDocumentText, ClassificationResult, extractPersonNameFromDirectory } from './documentClassifier';

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

/**
 * Invokes photoDetector.py to visually identify if the image is a passport/ID photo
 */
export function tryPassportPhotoDetector(imagePath: string): { isPassport: boolean; confidence: number; reason?: string } {
  const pyScript = path.resolve(__dirname, 'photoDetector.py');
  try {
    const output = execSync(`python "${pyScript}" "${imagePath}"`, { stdio: 'pipe' }).toString();
    const parsed = JSON.parse(output);
    if (parsed && parsed.is_passport_photo) {
      return {
        isPassport: true,
        confidence: parsed.confidence || 0.9,
        reason: parsed.reason
      };
    }
  } catch {}
  return { isPassport: false, confidence: 0 };
}

/**
 * Invokes signatureDetector.py to visually identify if the image is a signature scan
 */
export function trySignatureDetector(imagePath: string): { isSignature: boolean; confidence: number; inkType?: string; reason?: string } {
  const pyScript = path.resolve(__dirname, 'signatureDetector.py');
  try {
    const output = execSync(`python "${pyScript}" "${imagePath}"`, { stdio: 'pipe' }).toString();
    const parsed = JSON.parse(output);
    if (parsed && parsed.is_signature) {
      return {
        isSignature: true,
        confidence: parsed.confidence || 0.85,
        inkType: parsed.ink_type,
        reason: parsed.reason
      };
    }
  } catch {}
  return { isSignature: false, confidence: 0 };
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

  let classification = classifyDocumentText(extractedText, path.basename(imagePath), path.dirname(imagePath));

  // 3. Visual Detection Fallbacks (when text is minimal or document is unknown)
  if (extractedText.trim().length < 35 || classification.docType === 'document') {
    const photoRes = tryPassportPhotoDetector(imagePath);
    if (photoRes.isPassport) {
      const ext = path.extname(imagePath) || '.jpg';
      const dirPersonName = extractPersonNameFromDirectory(options.targetDir || path.dirname(imagePath));
      const name = classification.extractedName || dirPersonName || 'applicant';
      classification = {
        docType: 'passport_photo',
        docTypeName: 'Passport Size Photo',
        extractedName: name,
        matchedKeywords: ['visual_face_geometry'],
        confidence: photoRes.confidence,
        suggestedFilename: `passport_photo_${name}${ext}`
      };
      console.log(`   📸 Visual Detection: Passport Size Photo Confirmed (${Math.round(photoRes.confidence * 100)}%)`);
    } else {
      // Check for Signature Scan (Blue / Dark ink rectangular image)
      const signRes = trySignatureDetector(imagePath);
      if (signRes.isSignature) {
        const ext = path.extname(imagePath) || '.jpg';
        const dirPersonName = extractPersonNameFromDirectory(options.targetDir || path.dirname(imagePath));
        const name = classification.extractedName || dirPersonName || 'applicant';
        classification = {
          docType: 'signature',
          docTypeName: 'Signature',
          extractedName: name,
          matchedKeywords: ['visual_ink_geometry', signRes.inkType || 'blue_ink'],
          confidence: signRes.confidence,
          suggestedFilename: `signature_${name}${ext}`
        };
        console.log(`   ✍️ Visual Detection: Signature Confirmed (${Math.round(signRes.confidence * 100)}% - ${signRes.inkType}) -> Person: ${name}`);
      }
    }
  }

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
