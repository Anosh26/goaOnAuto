/**
 * Batch Document Scanner & Classification Orchestrator.
 * Single Responsibility: Coordinates batch GPU OCR, visual verification, and document classification.
 */
import * as path from 'path';
import * as fs from 'fs';
import { createWorker } from 'tesseract.js';
import { classifyDocumentText, ClassificationResult, extractPersonNameFromDirectory } from '../classifier';
import { GpuDaemonClient } from './gpuDaemonClient';
import { tryPassportPhotoDetector, trySignatureDetector } from './visualDetectors';

export interface ScanOptions {
  autoRename?: boolean;
  targetDir?: string;
  workerLang?: string;
}

export interface BatchScanResult {
  imagePath: string;
  classification: ClassificationResult;
  newPath?: string;
}

/**
 * Processes a batch of document images simultaneously using the persistent GPU worker daemon.
 */
export async function processDocumentImagesBatch(
  imagePaths: string[],
  options: ScanOptions = {}
): Promise<BatchScanResult[]> {
  if (imagePaths.length === 0) return [];

  const startTime = Date.now();
  const daemon = GpuDaemonClient.getInstance();
  const daemonResponse = await daemon.batchProcess(imagePaths);

  const results: BatchScanResult[] = [];

  if (daemonResponse && daemonResponse.results && daemonResponse.results.length > 0) {
    const device = daemonResponse.device ?? 'GPU CUDA';
    console.log(`   ⚡ GPU Batch Processed (${imagePaths.length} documents in ${Date.now() - startTime}ms) via ${device}`);

    for (const item of daemonResponse.results) {
      const imgPath = item.path;
      let classification = classifyDocumentText(item.text, path.basename(imgPath), path.dirname(imgPath));

      // Visual detection fallback from GPU daemon output
      if (item.text.trim().length < 35 || classification.docType === 'document') {
        if (item.is_photo) {
          const ext = path.extname(imgPath) || '.jpg';
          const dirPersonName = extractPersonNameFromDirectory(options.targetDir || path.dirname(imgPath));
          const name = classification.extractedName || dirPersonName || 'applicant';
          classification = {
            docType: 'passport_photo',
            docTypeName: 'Passport Size Photo',
            extractedName: name,
            matchedKeywords: ['visual_face_geometry'],
            confidence: item.photo_confidence || 0.9,
            suggestedFilename: `passport_photo_${name}${ext}`,
          };
          console.log(`   📸 Visual Detection: Passport Photo Confirmed (${Math.round((item.photo_confidence || 0.9) * 100)}%) -> Person: ${name}`);
        } else if (item.is_signature) {
          const ext = path.extname(imgPath) || '.jpg';
          const dirPersonName = extractPersonNameFromDirectory(options.targetDir || path.dirname(imgPath));
          const name = classification.extractedName || dirPersonName || 'applicant';
          classification = {
            docType: 'signature',
            docTypeName: 'Signature',
            extractedName: name,
            matchedKeywords: ['visual_ink_geometry', item.signature_ink || 'blue_ink'],
            confidence: item.signature_confidence || 0.85,
            suggestedFilename: `signature_${name}${ext}`,
          };
          console.log(`   ✍️ Visual Detection: Signature Confirmed (${Math.round((item.signature_confidence || 0.85) * 100)}%) -> Person: ${name}`);
        }
      }

      let newPath: string | undefined = undefined;
      if (options.autoRename) {
        const dir = options.targetDir || path.dirname(imgPath);
        let targetName = classification.suggestedFilename;
        let targetPath = path.join(dir, targetName);

        let counter = 1;
        const ext = path.extname(targetName);
        const stem = path.basename(targetName, ext);

        while (fs.existsSync(targetPath) && targetPath !== imgPath) {
          targetName = `${stem}_${counter}${ext}`;
          targetPath = path.join(dir, targetName);
          counter++;
        }

        fs.renameSync(imgPath, targetPath);
        newPath = targetPath;
      }

      results.push({ imagePath: imgPath, classification, newPath });
    }

    return results;
  }

  // Fallback: Individual processing if daemon is unavailable
  for (const imgPath of imagePaths) {
    const singleRes = await processDocumentImage(imgPath, options);
    results.push({ imagePath: imgPath, classification: singleRes.classification, newPath: singleRes.newPath });
  }

  return results;
}

/**
 * Process single document image. Uses persistent GPU worker daemon or fallback.
 */
export async function processDocumentImage(
  imagePath: string,
  options: ScanOptions = {}
): Promise<{ classification: ClassificationResult; newPath?: string }> {
  if (!fs.existsSync(imagePath)) {
    throw new Error(`File not found: ${imagePath}`);
  }

  const batchResults = await processDocumentImagesBatch([imagePath], options);
  if (batchResults.length > 0) {
    return {
      classification: batchResults[0]!.classification,
      newPath: batchResults[0]!.newPath,
    };
  }

  // Fallback to CPU WASM Tesseract.js
  const worker = await createWorker(options.workerLang || 'eng');
  let extractedText = '';
  try {
    const {
      data: { text },
    } = await worker.recognize(imagePath);
    extractedText = text;
  } finally {
    await worker.terminate();
  }

  const classification = classifyDocumentText(extractedText, path.basename(imagePath), path.dirname(imagePath));
  return { classification };
}

export { tryPassportPhotoDetector, trySignatureDetector };
