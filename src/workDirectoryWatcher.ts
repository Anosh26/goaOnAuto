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
import { synthesizeDossier, ExtractedDocument } from './classifier';
import { GpuDaemonClient, AadhaarQrResult } from './scanner/gpuDaemonClient';

import { SystemGovernor } from './watcher/systemGovernor';
import { requestHumanConfirmation } from './gui/confirmationBridge';

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

const watcherService = new WatcherService(config.workDir);
let isProcessing = false;

async function processDirtyNodes(dirtyNodes: DirectoryNode[]) {
  if (isProcessing || dirtyNodes.length === 0) return;
  isProcessing = true;

  try {
    // Enforce system resource governor (keep >= 3GB RAM free, >= 20% CPU free)
    await SystemGovernor.getInstance().ensureResourceAvailability();

    for (const node of dirtyNodes) {
      const candidateFiles: string[] = [];

      for (const [filename, fileRecord] of node.changedFiles.entries()) {
        if (filename.startsWith('.') || filename.startsWith('~$') || filename.includes('.tmp') || filename.includes('.~lock') || filename.endsWith('.gdrive')) {
          continue;
        }

        if (filename.includes('_white_bg') || filename.includes('_processed')) continue;
        if (filename.match(/(aadhaar|pan|pcc|residence_cert|caste_cert|obc_cert|marriage_cert|birth_cert|bonafide_cert|electricity_bill|house_tax|ration_card|passport|driving_license|voter_id|marksheet|samaj_cert|passport_photo|signature)_/i) || filename.match(/_(signature|white_bg|processed)\./i)) {
          continue;
        }

        if (fs.existsSync(fileRecord.filePath)) {
          try {
            const stats = fs.statSync(fileRecord.filePath);
            if (!stats.isFile()) continue;

            const isReady = await waitForFileReady(fileRecord.filePath);
            if (isReady) {
              candidateFiles.push(fileRecord.filePath);
            }
          } catch {}
        }
      }

      if (candidateFiles.length === 0) continue;

      candidateFiles.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));

      console.log(`\n🔍 [Dirty Bit = 1] Change Detected at Dynamic Path: ${node.fullPath}`);
      console.log(`   📄 Candidate Documents (${candidateFiles.length}): ${candidateFiles.map(f => path.basename(f)).join(', ')}`);

      // 1. Stage all candidate files locally
      const stagedItems: Array<{ srcPath: string; stagedPath: string }> = [];
      for (const srcPath of candidateFiles) {
        const stagedPath = path.join(config.stagingDir, `${Date.now()}_${path.basename(srcPath)}`);
        fs.copyFileSync(srcPath, stagedPath);
        stagedItems.push({ srcPath, stagedPath });
      }

      // 2. Perform Batch GPU OCR & Document Classification simultaneously
      const stagedPaths = stagedItems.map(item => item.stagedPath);
      const batchResults = await processDocumentImagesBatch(stagedPaths, {
        autoRename: false,
        targetDir: node.fullPath
      });

      // 3. Process renamed files & outputs
      for (let i = 0; i < stagedItems.length; i++) {
        const { srcPath, stagedPath } = stagedItems[i]!;
        const scanRes = batchResults[i];
        if (!scanRes) continue;

        let classRes = scanRes.classification;

        // Interactive Raylib Human Confirmation System
        if (config.enableHumanConfirmation) {
          console.log(`   🎨 Opening Raylib Human Confirmation GUI for: ${path.basename(srcPath)}...`);
          const confirmRes = await requestHumanConfirmation({
            filePath: stagedPath,
            docType: classRes.docType,
            docTypeName: classRes.docTypeName,
            extractedName: classRes.extractedName,
            confidence: classRes.confidence
          });

          if (confirmRes.action === 'skipped') {
            console.log(`   ⏭️ User Skipped Document: ${path.basename(srcPath)} (File left un-renamed)`);
            safeUnlink(stagedPath);
            continue;
          }

          if (confirmRes.action === 'changed') {
            classRes = {
              ...classRes,
              docType: confirmRes.docType,
              docTypeName: confirmRes.docTypeName,
              extractedName: confirmRes.extractedName || classRes.extractedName,
              suggestedFilename: `${confirmRes.docType}_${confirmRes.extractedName || 'confirmed'}${path.extname(srcPath)}`
            };
            console.log(`   ✏️ Category Overridden by Human: ${classRes.docTypeName} (${classRes.docType})`);
          }
        }

        const ext = path.extname(srcPath);
        const nameStr = classRes.extractedName ? `_${classRes.extractedName}` : '_scanned';
        const baseStem = `${classRes.docType}${nameStr}`;
        let newFilename = `${baseStem}${ext}`;
        let finalPath = path.join(node.fullPath, newFilename);

        let counter = 1;
        while (fs.existsSync(finalPath) && finalPath !== srcPath) {
          newFilename = `${baseStem}_${counter}${ext}`;
          finalPath = path.join(node.fullPath, newFilename);
          counter++;
        }

        fs.copyFileSync(stagedPath, finalPath);
        console.log(`   ✅ Document Identified: ${classRes.docTypeName} (${Math.round(classRes.confidence * 100)}% confidence)`);
        console.log(`   ✨ Renamed Safely : ${newFilename}`);

        // If it is a passport photo, generate a white background copy with 50% resize (< 50KB) using RTX 4060 GPU
        if (classRes.docType === 'passport_photo') {
          try {
            const whiteBgFilename = `${baseStem}_white_bg${ext}`;
            const whiteBgPath = path.join(node.fullPath, whiteBgFilename);
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
      
      const dossierPath = path.join(node.fullPath, 'applicant_dossier.json');
      fs.writeFileSync(dossierPath, JSON.stringify(dossier, null, 2));
      console.log(`   📄 Saved Applicant Dossier: applicant_dossier.json`);

    }
  } catch (err: any) {
    console.error(`   ❌ Error during Drive-safe batch processing:`, err.message || err);
  } finally {
    watcherService.getBuffer().resetBuffer();
    isProcessing = false;
  }
}

watcherService.start((dirtyNodes) => {
  processDirtyNodes(dirtyNodes);
});

console.log(`👀 Watching for document additions in ${config.workDir}...`);
console.log(`(Press Ctrl+C to exit)\n`);
