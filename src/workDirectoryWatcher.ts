import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { DirectoryChangeBuffer, DirectoryNode } from '../utils/directoryChangeBuffer';
import { processDocumentImage } from '../utils/documentScanner';
import { processPhotoForUpload } from '../utils/imageProcessor';

// Load .env manually
function loadEnv() {
  const envPath = path.resolve(process.cwd(), '.env');
  if (fs.existsSync(envPath)) {
    const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const [key, ...valParts] = trimmed.split('=');
      if (key && valParts.length > 0) {
        const val = valParts.join('=').trim().replace(/^["']|["']$/g, '');
        if (!process.env[key.trim()]) {
          process.env[key.trim()] = val;
        }
      }
    }
  }
}

loadEnv();

const WORK_DIR = process.env.DOCUMENT_WATCH_PATH || process.env.WORK_DIR_PATH || path.resolve('./work_directory');
const STAGING_DIR = path.join(os.tmpdir(), 'goaOnAuto_drive_stage');

if (!fs.existsSync(WORK_DIR)) {
  console.log(`📁 Creating Work Directory: ${WORK_DIR}`);
  fs.mkdirSync(WORK_DIR, { recursive: true });
}

if (!fs.existsSync(STAGING_DIR)) {
  fs.mkdirSync(STAGING_DIR, { recursive: true });
}

console.log(`===================================================`);
console.log(`🚀 GoaOnAuto Work Directory Automated Document Watcher`);
console.log(`🛡️  Google Drive Lock-Safe & Anti-Flagging Engine Enabled`);
console.log(`📂 Monitoring Root Work Dir: ${WORK_DIR}`);
console.log(`===================================================\n`);

const buffer = new DirectoryChangeBuffer(WORK_DIR);
const SUPPORTED_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.pdf']);

let isProcessing = false;

/**
 * Wait until Google Drive finishes writing/syncing the file to disk
 */
async function waitForFileReady(filePath: string, maxWaitMs = 5000): Promise<boolean> {
  const start = Date.now();
  let lastSize = -1;

  while (Date.now() - start < maxWaitMs) {
    try {
      if (!fs.existsSync(filePath)) return false;
      const stats = fs.statSync(filePath);
      if (!stats.isFile()) return false; // Ignore directories

      if (stats.size > 0 && stats.size === lastSize) {
        return true; // File is stable
      }
      lastSize = stats.size;
    } catch {}
    await new Promise(r => setTimeout(r, 300));
  }
  return fs.existsSync(filePath) && fs.statSync(filePath).isFile();
}

/**
 * Safe file deletion to prevent Google Drive EBUSY / locking exceptions
 */
function safeUnlink(filePath: string, retries = 5): void {
  for (let i = 0; i < retries; i++) {
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
      return;
    } catch (e) {
      if (i === retries - 1) console.warn(`⚠️ Could not remove original file (Google Drive locked): ${path.basename(filePath)}`);
      // Brief sleep before retry
      const end = Date.now() + 200;
      while (Date.now() < end) {}
    }
  }
}

async function processDirtyNodes(dirtyNodes: DirectoryNode[]) {
  if (isProcessing || dirtyNodes.length === 0) return;
  isProcessing = true;

  try {
    for (const node of dirtyNodes) {
      const candidateFiles: string[] = [];

      for (const [filename, fileRecord] of node.changedFiles.entries()) {
        const ext = path.extname(filename).toLowerCase();
        
        // Skip Google Drive temporary files, locks, or already processed files
        if (filename.startsWith('.') || filename.startsWith('~$') || filename.includes('.tmp') || filename.includes('.~lock') || filename.endsWith('.gdrive')) {
          continue;
        }

        // Skip already processed files or generated outputs
        if (filename.includes('_white_bg') || filename.includes('_processed')) continue;
        if (filename.match(/(aadhaar|pan|pcc|residence_cert|caste_cert|obc_cert|marriage_cert|birth_cert|bonafide_cert|electricity_bill|house_tax|ration_card|passport|driving_license|voter_id|marksheet|samaj_cert|passport_photo)_/i)) {
          continue;
        }

        if (fs.existsSync(fileRecord.filePath)) {
          try {
            const stats = fs.statSync(fileRecord.filePath);
            if (!stats.isFile()) continue; // Skip directories!

            // Verify file stability (Google Drive sync complete)
            const isReady = await waitForFileReady(fileRecord.filePath);
            if (isReady) {
              candidateFiles.push(fileRecord.filePath);
            }
          } catch {}
        }
      }

      if (candidateFiles.length === 0) continue;

      // Sort files sequentially
      candidateFiles.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));

      console.log(`\n🔍 [Dirty Bit = 1] Change Detected at Dynamic Path: ${node.fullPath}`);
      console.log(`   📄 Candidate Documents (${candidateFiles.length}): ${candidateFiles.map(f => path.basename(f)).join(', ')}`);

      // Copy candidate files to local staging directory (outside Google Drive sync path) to prevent Drive locks/flags
      const stagedClassifications = [];
      for (const srcPath of candidateFiles) {
        const stagedPath = path.join(STAGING_DIR, `${Date.now()}_${path.basename(srcPath)}`);
        fs.copyFileSync(srcPath, stagedPath);

        const res = await processDocumentImage(stagedPath, { autoRename: false });
        stagedClassifications.push({ srcPath, stagedPath, classification: res.classification });
      }

      // Process each document individually (no automatic merging)
      for (const item of stagedClassifications) {
        const classRes = item.classification;
        const ext = path.extname(item.srcPath);
        const nameStr = classRes.extractedName ? `_${classRes.extractedName}` : '_scanned';
        const baseStem = `${classRes.docType}${nameStr}`;
        let newFilename = `${baseStem}${ext}`;
        let finalPath = path.join(node.fullPath, newFilename);

        // Ensure unique filename if destination exists or multiple files share name
        let counter = 1;
        while (fs.existsSync(finalPath) && finalPath !== item.srcPath) {
          newFilename = `${baseStem}_${counter}${ext}`;
          finalPath = path.join(node.fullPath, newFilename);
          counter++;
        }

        fs.copyFileSync(item.stagedPath, finalPath);
        console.log(`   ✅ Document Identified: ${classRes.docTypeName} (${Math.round(classRes.confidence * 100)}% confidence)`);
        console.log(`   ✨ Renamed Safely : ${newFilename}`);

        // If it is a passport photo, generate a white background copy with 50% resize (< 50KB) using GPU if found or CPU
        if (classRes.docType === 'passport_photo') {
          try {
            const whiteBgFilename = `${baseStem}_white_bg${ext}`;
            const whiteBgPath = path.join(node.fullPath, whiteBgFilename);
            console.log(`   🎨 Generating AI White Background Copy (50% scale, <50KB) via GPU/CPU auto-select...`);
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

        // Remove original & staged file
        if (finalPath !== item.srcPath) {
          safeUnlink(item.srcPath);
        }
        safeUnlink(item.stagedPath);
      }
    }
  } catch (err: any) {
    console.error(`   ❌ Error during Drive-safe batch processing:`, err.message || err);
  } finally {
    buffer.resetBuffer();
    isProcessing = false;
  }
}

// Start active filesystem watcher with dirty bit propagation & DFS traversal
buffer.startWatching((dirtyNodes) => {
  processDirtyNodes(dirtyNodes);
});

console.log(`👀 Watching for document additions in ${WORK_DIR}...`);
console.log(`(Press Ctrl+C to exit)\n`);
