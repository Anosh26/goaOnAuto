import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { DirectoryChangeBuffer, DirectoryNode } from '../utils/directoryChangeBuffer';
import { processDocumentImage } from '../utils/documentScanner';
import { mergeCardFrontBackVertically, convertImagesToMultipagePdf } from '../utils/imageOpsWrapper';

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
      const size = fs.statSync(filePath).size;
      if (size > 0 && size === lastSize) {
        return true; // File is stable
      }
      lastSize = size;
    } catch {}
    await new Promise(r => setTimeout(r, 300));
  }
  return fs.existsSync(filePath);
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
        if (filename.includes('_merged') || filename.endsWith('.pdf')) continue;
        if (filename.match(/(aadhaar|pan|pcc|residence_cert|caste_cert|obc_cert|marriage_cert|birth_cert|bonafide_cert|electricity_bill|house_tax|ration_card|passport|driving_license|voter_id)_/i)) {
          continue;
        }

        if (fs.existsSync(fileRecord.filePath)) {
          // Verify file stability (Google Drive sync complete)
          const isReady = await waitForFileReady(fileRecord.filePath);
          if (isReady) {
            candidateFiles.push(fileRecord.filePath);
          }
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

      const docTypes = stagedClassifications.map(c => c.classification.docType);
      const isVoterOrCard = docTypes.some(t => ['voter_id', 'aadhaar', 'pan', 'driving_license'].includes(t));
      const isMarriageCert = docTypes.some(t => t === 'marriage_cert');

      // CASE 1: Card ID (Voter ID, Aadhaar, PAN, DL) with Front & Back side images (2 sequential files)
      if (isVoterOrCard && candidateFiles.length >= 2) {
        const frontItem = stagedClassifications[0];
        const backItem = stagedClassifications[1];

        if (frontItem && backItem) {
          console.log(`   🪪 ID Card Pair Detected (Front & Back). Merging vertically in Staging...`);
          
          const primaryClass = frontItem.classification;
          const ext = path.extname(frontItem.srcPath);
          const mergedFilename = `${primaryClass.docType}_${primaryClass.extractedName || 'card'}_merged${ext}`;
          
          const stagedMergedPath = path.join(STAGING_DIR, mergedFilename);
          const finalOutputPath = path.join(node.fullPath, mergedFilename);

          mergeCardFrontBackVertically(frontItem.stagedPath, backItem.stagedPath, stagedMergedPath);
          
          // Copy merged file cleanly back to Google Drive directory
          fs.copyFileSync(stagedMergedPath, finalOutputPath);
          console.log(`   ✨ Merged Card Saved: ${mergedFilename}`);

          // Cleanup staging files & original raw scans
          safeUnlink(frontItem.stagedPath);
          safeUnlink(backItem.stagedPath);
          safeUnlink(stagedMergedPath);
          safeUnlink(frontItem.srcPath);
          safeUnlink(backItem.srcPath);
        }
      }
      // CASE 2: Marriage Certificate (or Civil Registration) -> Convert to Multipage PDF
      else if (isMarriageCert) {
        console.log(`   📜 Marriage Certificate / Civil Registration Document Detected. Creating Multipage PDF...`);

        const primaryItem = stagedClassifications.find(c => c.classification.docType === 'marriage_cert') || stagedClassifications[0];
        const docType = primaryItem?.classification.docType || 'marriage_cert';
        const rawName = primaryItem?.classification.extractedName || 'certificate';
        const cleanName = rawName.replace(/\.pdf.*$/i, '').replace(/[^a-z0-9]/gi, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '');
        const pdfFilename = `${docType}_${cleanName || 'certificate'}.pdf`;
        
        const stagedPdfPath = path.join(STAGING_DIR, pdfFilename);
        const finalPdfPath = path.join(node.fullPath, pdfFilename);

        const stagedImagePaths = stagedClassifications.map(c => c.stagedPath);
        convertImagesToMultipagePdf(stagedImagePaths, stagedPdfPath);

        // Copy final PDF to Google Drive directory
        fs.copyFileSync(stagedPdfPath, finalPdfPath);
        console.log(`   ✨ Multipage PDF Saved: ${pdfFilename}`);

        // Cleanup staging & original files
        stagedClassifications.forEach(item => {
          safeUnlink(item.stagedPath);
          if (path.extname(item.srcPath).toLowerCase() !== '.pdf') {
            safeUnlink(item.srcPath);
          }
        });
        safeUnlink(stagedPdfPath);
      }
      // CASE 3: Single documents -> Rename safely in-place via Staging
      else {
        for (const item of stagedClassifications) {
          const classRes = item.classification;
          const ext = path.extname(item.srcPath);
          const nameStr = classRes.extractedName ? `_${classRes.extractedName}` : '_scanned';
          const newFilename = `${classRes.docType}${nameStr}${ext}`;
          const finalPath = path.join(node.fullPath, newFilename);

          fs.copyFileSync(item.stagedPath, finalPath);
          console.log(`   ✅ Document Identified: ${classRes.docTypeName} (${Math.round(classRes.confidence * 100)}% confidence)`);
          console.log(`   ✨ Renamed Safely : ${newFilename}`);

          // Remove original & staged file
          if (finalPath !== item.srcPath) {
            safeUnlink(item.srcPath);
          }
          safeUnlink(item.stagedPath);
        }
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
