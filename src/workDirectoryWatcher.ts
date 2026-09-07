/**
 * GoaOnAuto Work Directory Automated Document Watcher Entrypoint.
 * Single Responsibility: Bootstraps the application, monitors the directory, and orchestrates batch document pipeline.
 */
import * as path from 'path';
import * as fs from 'fs';
import { config } from './config';
import { DirectoryNode } from './watcher/directoryBuffer';
import { WatcherService } from './watcher/watcherService';
import { waitForFileReady, safeUnlink } from './watcher/fileSyncReady';
import { processDocumentImagesBatch } from './scanner/documentScanner';
import { processPhotoForUpload } from './image/photoProcessor';
import { synthesizeDossier, ExtractedDocument, ClassificationResult } from './classifier';
import { GpuDaemonClient, AadhaarQrResult } from './scanner/gpuDaemonClient';

import { SystemGovernor } from './watcher/systemGovernor';
import { requestHumanConfirmation, ConfirmationResult } from './gui/confirmationBridge';
import { ProgressBridge } from './gui/progressBridge';

if (!fs.existsSync(config.workDir)) {
  console.log(`📁 Creating Work Directory: ${config.workDir}`);
  fs.mkdirSync(config.workDir, { recursive: true });
}

if (!fs.existsSync(config.stagingDir)) {
  fs.mkdirSync(config.stagingDir, { recursive: true });
}

console.log(`===================================================`);
console.log(`🚀 GoaOnAuto Work Directory Automated Document Watcher`);
console.log(`⚡ RTX 4060 GPU Persistent Batch Engine Active (90% Cap)`);
console.log(`🛡️  System Governor: Free RAM ≥ 3GB | Free CPU ≥ 20%`);
console.log(`🎨 Raylib GPU Human Confirmation GUI System Enabled`);
console.log(`📂 Monitoring Root Work Dir: ${config.workDir}`);
console.log(`===================================================\n`);

interface QueuedBatch {
  directoryPath: string;
  files: string[];
}

const watcherService = new WatcherService(config.workDir);
const taskQueue: QueuedBatch[] = [];
let isProcessingQueue = false;

function saveToDataset(
  stagedPath: string,
  aiClassification: ClassificationResult,
  confirmRes: ConfirmationResult
): void {
  try {
    const datasetDir = path.resolve(config.projectRoot, 'dataset');
    const correctionsPath = path.join(datasetDir, 'corrections.jsonl');
    const rawCategoryDir = path.join(datasetDir, 'raw', confirmRes.docType);

    if (!fs.existsSync(rawCategoryDir)) {
      fs.mkdirSync(rawCategoryDir, { recursive: true });
    }

    // 1. Copy sample document to dataset/raw/<category>/
    const baseName = path.basename(stagedPath);
    let targetPath = path.join(rawCategoryDir, baseName);
    let counter = 1;
    const ext = path.extname(baseName);
    const stem = path.basename(baseName, ext);
    while (fs.existsSync(targetPath)) {
      targetPath = path.join(rawCategoryDir, `${stem}_${counter}${ext}`);
      counter++;
    }
    fs.copyFileSync(stagedPath, targetPath);
    console.log(`   📥 Saved to Dataset: dataset/raw/${confirmRes.docType}/${path.basename(targetPath)}`);

    // 2. Append to dataset/corrections.jsonl for classifier retraining
    const entry = {
      timestamp: new Date().toISOString(),
      filePath: targetPath,
      fileName: path.basename(targetPath),
      aiDetected: aiClassification.docType,
      aiDetectedName: aiClassification.docTypeName,
      aiConfidence: aiClassification.confidence,
      humanVerified: confirmRes.docType,
      humanVerifiedName: confirmRes.docTypeName,
      action: confirmRes.action,
      extractedName: confirmRes.extractedName || aiClassification.extractedName || '',
      customKeyword: confirmRes.customKeyword || '',
      matchedKeywords: aiClassification.matchedKeywords || []
    };
    fs.appendFileSync(correctionsPath, JSON.stringify(entry) + '\n', 'utf-8');
  } catch (err: any) {
    console.warn(`   ⚠️ Notice: Could not record to dataset:`, err.message || err);
  }
}

function enqueueDirtyNodes(dirtyNodes: DirectoryNode[]) {
  if (dirtyNodes.length === 0) return;

  const newBatches: QueuedBatch[] = [];

  for (const node of dirtyNodes) {
    const candidateFiles: string[] = [];

    for (const [filename, fileRecord] of node.changedFiles.entries()) {
      if (
        filename.startsWith('.') ||
        filename.startsWith('~$') ||
        filename.includes('.tmp') ||
        filename.includes('.~lock') ||
        filename.endsWith('.gdrive')
      ) {
        continue;
      }

      const extLower = path.extname(filename).toLowerCase();
      if (!['.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx'].includes(extLower)) {
        continue;
      }

      if (filename.includes('_white_bg') || filename.includes('_processed')) continue;
      if (
        filename.match(
          /(aadhaar|pan|pcc|residence_cert|caste_cert|obc_cert|marriage_cert|birth_cert|bonafide_cert|electricity_bill|house_tax|ration_card|passport|driving_license|voter_id|marksheet|samaj_cert|passport_photo|signature)_/i
        ) ||
        filename.match(/_(signature|white_bg|processed)\./i)
      ) {
        continue;
      }

      candidateFiles.push(fileRecord.filePath);
    }

    if (candidateFiles.length > 0) {
      newBatches.push({
        directoryPath: node.fullPath,
        files: candidateFiles
      });
    }
  }

  // Clear buffer tree now that candidate files are safely snapshotted
  watcherService.getBuffer().resetBuffer();

  if (newBatches.length > 0) {
    taskQueue.push(...newBatches);

    ProgressBridge.getInstance().update({
      queue_length: taskQueue.length,
      status: isProcessingQueue ? 'Batches queued in background...' : 'Documents detected, preparing batch...'
    });

    if (!isProcessingQueue) {
      processQueue();
    }
  }
}

async function processQueue() {
  if (isProcessingQueue) return;
  isProcessingQueue = true;
  const progressBridge = ProgressBridge.getInstance();

  try {
    while (taskQueue.length > 0) {
      const batch = taskQueue.shift()!;
      const dirPath = batch.directoryPath;

      progressBridge.update({
        queue_length: taskQueue.length,
        status: `Verifying files in ${path.basename(dirPath)}...`,
        current_file: path.basename(dirPath),
        progress_percent: 5
      });

      // Wait for files to finish syncing / writing to disk
      const readyFiles: string[] = [];
      for (const filePath of batch.files) {
        if (fs.existsSync(filePath)) {
          try {
            const stats = fs.statSync(filePath);
            if (!stats.isFile()) continue;

            const isReady = await waitForFileReady(filePath);
            if (isReady) {
              readyFiles.push(filePath);
            }
          } catch {}
        }
      }

      if (readyFiles.length === 0) continue;

      readyFiles.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));

      console.log(`\n🔍 [Dirty Bit = 1] Change Detected at Dynamic Path: ${dirPath}`);
      console.log(`   📄 Candidate Documents (${readyFiles.length}): ${readyFiles.map(f => path.basename(f)).join(', ')}`);

      // Enforce system resource governor (keep >= 3GB RAM free, >= 20% CPU free)
      await SystemGovernor.getInstance().ensureResourceAvailability();

      // 1. Stage all candidate files locally
      progressBridge.update({
        queue_length: taskQueue.length,
        status: `Staging ${readyFiles.length} documents...`,
        current_file: path.basename(readyFiles[0]!),
        progress_percent: 15
      });

      const stagedItems: Array<{ srcPath: string; stagedPath: string }> = [];
      for (const srcPath of readyFiles) {
        const stagedPath = path.join(config.stagingDir, `${Date.now()}_${path.basename(srcPath)}`);
        fs.copyFileSync(srcPath, stagedPath);
        stagedItems.push({ srcPath, stagedPath });
      }

      // 2. Perform Batch GPU OCR & Document Classification simultaneously
      progressBridge.update({
        queue_length: taskQueue.length,
        status: `⚡ GPU Batch OCR Running (${readyFiles.length} docs)...`,
        current_file: `${readyFiles.length} documents`,
        progress_percent: 40
      });

      const stagedPaths = stagedItems.map(item => item.stagedPath);
      const batchResults = await processDocumentImagesBatch(stagedPaths, {
        autoRename: false,
        targetDir: dirPath
      });

      // 3. Process renamed files & outputs
      for (let i = 0; i < stagedItems.length; i++) {
        const { srcPath, stagedPath } = stagedItems[i]!;
        const scanRes = batchResults[i];
        if (!scanRes) continue;

        let classRes = scanRes.classification;
        const initialAiClassification = { ...classRes };
        const currentFilename = path.basename(srcPath);

        progressBridge.update({
          queue_length: taskQueue.length,
          status: `🎨 Awaiting Verification: ${classRes.docTypeName}`,
          current_file: currentFilename,
          progress_percent: 55 + Math.round((i / stagedItems.length) * 35)
        });

        // Interactive Raylib Human Confirmation System
        if (config.enableHumanConfirmation) {
          console.log(`   🎨 Opening Raylib Human Confirmation GUI for: ${currentFilename}...`);
          const confirmRes = await requestHumanConfirmation({
            filePath: stagedPath,
            docType: classRes.docType,
            docTypeName: classRes.docTypeName,
            extractedName: classRes.extractedName,
            confidence: classRes.confidence
          });

          if (confirmRes.action === 'skipped') {
            console.log(`   ⏭️ User Skipped Document: ${currentFilename} (File left un-renamed)`);
            safeUnlink(stagedPath);
            continue;
          }

          if (confirmRes.action === 'changed') {
            classRes = {
              ...classRes,
              docType: confirmRes.docType,
              docTypeName: confirmRes.docTypeName,
              extractedName: confirmRes.extractedName || classRes.extractedName,
              suggestedFilename: `${confirmRes.docType}_${(confirmRes.extractedName || 'confirmed').replace(/[<>:"/\\|?*\x00-\x1F]/g, '_')}${path.extname(srcPath)}`
            };
            console.log(`   ✏️ Category Overridden by Human: ${classRes.docTypeName} (${classRes.docType})`);
          }

          // Save verified / corrected document into ground-truth dataset for retrain learning
          saveToDataset(stagedPath, initialAiClassification, confirmRes);
        }

        const ext = path.extname(srcPath);
        const rawName = classRes.extractedName || '';
        const safeName = rawName
          .replace(/[<>:"/\\|?*\x00-\x1F]/g, '_')
          .replace(/_+/g, '_')
          .replace(/^_+|_+$/g, '');
        const nameStr = safeName ? `_${safeName}` : '_scanned';
        const baseStem = `${classRes.docType}${nameStr}`;
        let newFilename = `${baseStem}${ext}`;
        let finalPath = path.join(dirPath, newFilename);

        let counter = 1;
        while (fs.existsSync(finalPath) && finalPath !== srcPath) {
          newFilename = `${baseStem}_${counter}${ext}`;
          finalPath = path.join(dirPath, newFilename);
          counter++;
        }

        fs.copyFileSync(stagedPath, finalPath);
        console.log(`   ✅ Document Identified: ${classRes.docTypeName} (${Math.round(classRes.confidence * 100)}% confidence)`);
        console.log(`   ✨ Renamed Safely : ${newFilename}`);

        // If it is a passport photo, generate a white background copy with 50% resize (< 50KB) using RTX 4060 GPU
        if (classRes.docType === 'passport_photo') {
          try {
            const whiteBgFilename = `${baseStem}_white_bg${ext}`;
            const whiteBgPath = path.join(dirPath, whiteBgFilename);
            console.log(`   🎨 Generating AI White Background Copy (50% scale, <50KB) via RTX 4060 GPU...`);
            await processPhotoForUpload(finalPath, {
              outputPath: whiteBgPath,
              maxKB: 50,
              useAI: true
            });
            console.log(`   ✨ White Background Photo Generated: ${whiteBgFilename}`);
          } catch (err: any) {
            console.warn(`   ⚠️ White background generation notice:`, err.message || err);
          }
        }

        if (finalPath !== srcPath) {
          safeUnlink(srcPath);
        }
        safeUnlink(stagedPath);
      }

      // After batch scanning all files in this directory, synthesize the Dossier
      const extractedDocs: ExtractedDocument[] = batchResults.filter(Boolean).map(res => ({
        docType: res.classification.docType,
        docTypeName: res.classification.docTypeName,
        rawText: res.rawText || '',
        filePath: res.newPath || res.imagePath,
        extractedName: res.classification.extractedName
      }));

      // Try to find an Aadhaar document and run QR scan on it
      let qrResult: AadhaarQrResult | null = null;
      const aadhaarDoc = extractedDocs.find(d => d.docType === 'aadhaar');
      if (aadhaarDoc) {
        console.log(`   🔍 Scanning Aadhaar QR code for ${path.basename(aadhaarDoc.filePath)}...`);
        const daemon = GpuDaemonClient.getInstance();
        qrResult = await daemon.aadhaarQrScan(aadhaarDoc.filePath);
        if (qrResult && qrResult.success) {
          console.log(`   ✅ Aadhaar QR Decode Success: Found ${qrResult.name}`);
        } else {
          console.log(`   ⚠️ Aadhaar QR not found or could not be decoded.`);
        }
      }

      const dossier = synthesizeDossier(extractedDocs, qrResult);
      const dossierPath = path.join(dirPath, 'applicant_dossier.json');
      fs.writeFileSync(dossierPath, JSON.stringify(dossier, null, 2));
      console.log(`   📄 Saved Applicant Dossier: applicant_dossier.json`);

      progressBridge.update({
        queue_length: taskQueue.length,
        status: `Completed batch for ${path.basename(dirPath)}`,
        current_file: `Dossier Saved`,
        progress_percent: 100
      });
    }
  } catch (err: any) {
    console.error(`   ❌ Error during batch processing:`, err.message || err);
  } finally {
    isProcessingQueue = false;
    // Keep window alive and return to clean idle status
    progressBridge.update({
      queue_length: taskQueue.length,
      status: `Watching for documents...`,
      current_file: `None (Idle)`,
      progress_percent: 0
    });
  }
}

// Launch single, stable Raylib progress window at startup
ProgressBridge.getInstance().ensureRunning();
ProgressBridge.getInstance().update({
  queue_length: 0,
  status: 'Watching for documents...',
  current_file: 'None (Idle)',
  progress_percent: 0
});

watcherService.start((dirtyNodes) => {
  enqueueDirtyNodes(dirtyNodes);
});

console.log(`👀 Watching for document additions in ${config.workDir}...`);
console.log(`(Press Ctrl+C to exit)\n`);

const handleExit = () => {
  console.log('\n🛑 Stopping GoaOnAuto Watcher and GUI...');
  watcherService.stop();
  ProgressBridge.getInstance().stop();
  process.exit(0);
};

process.on('SIGINT', handleExit);
process.on('SIGTERM', handleExit);
