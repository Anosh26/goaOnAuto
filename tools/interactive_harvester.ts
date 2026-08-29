/**
 * Interactive Dataset Harvester with Raylib Human Confirmation GUI.
 * Single Responsibility: Scans work directory, classifies documents via GPU OCR,
 * asks for human confirmation via Raylib GUI, copies confirmed files to dataset/raw/,
 * logs corrections, persists review history across sessions to prevent duplicates,
 * and auto-triggers retraining after threshold.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { config } from '../src/config';
import { processDocumentImagesBatch } from '../src/scanner/documentScanner';
import { requestHumanConfirmation, ConfirmationResult } from '../src/gui/confirmationBridge';

const SUPPORTED_EXTS = new Set(['.jpg', '.jpeg', '.png', '.pdf', '.bmp', '.webp']);
const HISTORY_PATH = path.resolve('./dataset/harvest_history.json');

interface CorrectionEntry {
  timestamp: string;
  filePath: string;
  fileName: string;
  aiDetected: string;
  aiDetectedName: string;
  aiConfidence: number;
  humanVerified: string;
  humanVerifiedName: string;
  action: 'confirmed' | 'changed' | 'skipped';
  extractedName: string;
  customKeyword?: string;
  matchedKeywords: string[];
}

interface HistoryRecord {
  filePath: string;
  fileName: string;
  decision: 'confirmed' | 'changed' | 'skipped';
  docType?: string;
  timestamp: string;
}

interface HarvestStats {
  totalScanned: number;
  confirmed: number;
  changed: number;
  skipped: number;
  copiedToDataset: number;
  categoryCounts: Record<string, number>;
}

function loadHarvestHistory(): Map<string, HistoryRecord> {
  const historyMap = new Map<string, HistoryRecord>();

  // 1. Load from dataset/harvest_history.json if present
  if (fs.existsSync(HISTORY_PATH)) {
    try {
      const data = JSON.parse(fs.readFileSync(HISTORY_PATH, 'utf-8'));
      if (data && typeof data === 'object') {
        for (const [normPath, record] of Object.entries(data)) {
          historyMap.set(normPath.toLowerCase(), record as HistoryRecord);
        }
      }
    } catch {}
  }

  // 2. Backfill from dataset/corrections.jsonl to ensure all previous runs are remembered
  const correctionsPath = path.resolve('./dataset/corrections.jsonl');
  if (fs.existsSync(correctionsPath)) {
    try {
      const lines = fs.readFileSync(correctionsPath, 'utf-8').split('\n').filter(Boolean);
      for (const line of lines) {
        try {
          const entry = JSON.parse(line);
          if (entry.filePath) {
            const key = entry.filePath.toLowerCase();
            if (!historyMap.has(key)) {
              historyMap.set(key, {
                filePath: entry.filePath,
                fileName: entry.fileName || path.basename(entry.filePath),
                decision: entry.action || 'confirmed',
                docType: entry.humanVerified || entry.aiDetected,
                timestamp: entry.timestamp || new Date().toISOString()
              });
            }
          }
        } catch {}
      }
    } catch {}
  }

  return historyMap;
}

function saveHarvestHistory(historyMap: Map<string, HistoryRecord>): void {
  try {
    const obj: Record<string, HistoryRecord> = {};
    for (const [key, val] of historyMap.entries()) {
      obj[key] = val;
    }
    fs.writeFileSync(HISTORY_PATH, JSON.stringify(obj, null, 2), 'utf-8');
  } catch (err: any) {
    console.warn('   ⚠️ Failed to save harvest_history.json:', err.message);
  }
}

function getAllFilesRecursively(dir: string): string[] {
  let results: string[] = [];
  if (!fs.existsSync(dir)) return results;

  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (
          entry.name.startsWith('.') ||
          entry.name === 'node_modules' ||
          entry.name === 'dataset' ||
          entry.name.includes('Trash') ||
          entry.name === '.venv' ||
          entry.name === '__pycache__' ||
          entry.name.toLowerCase().includes('temp') ||
          entry.name.toLowerCase().includes('tmp')
        ) {
          continue;
        }
        results = results.concat(getAllFilesRecursively(fullPath));
      } else if (entry.isFile()) {
        const lowerName = entry.name.toLowerCase();
        
        // Skip temporary, preview, lock, or office scratch files
        if (
          lowerName.startsWith('~$') ||
          lowerName.startsWith('.') ||
          lowerName.includes('.tmp') ||
          lowerName.includes('.gui_preview') ||
          lowerName.includes('.~lock') ||
          lowerName.endsWith('.gdrive')
        ) {
          continue;
        }

        const ext = path.extname(entry.name).toLowerCase();
        if (SUPPORTED_EXTS.has(ext)) {
          // Skip already-classified files (contain known docType prefix in filename)
          if (
            entry.name.includes('_white_bg') ||
            entry.name.includes('_processed') ||
            entry.name.match(
              /^(aadhaar|pan|pcc|residence_cert|caste_cert|obc_cert|marriage_cert|birth_cert|bonafide_cert|electricity_bill|house_tax|ration_card|passport|driving_license|voter_id|marksheet|samaj_cert|passport_photo|signature)_/i
            )
          ) {
            continue;
          }
          results.push(fullPath);
        }
      }
    }
  } catch {}
  return results;
}

function getExistingDatasetFiles(): Set<string> {
  const existing = new Set<string>();
  const datasetRawDir = path.resolve('./dataset/raw');

  if (fs.existsSync(datasetRawDir)) {
    const walkDataset = (dir: string) => {
      try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          const fullPath = path.join(dir, entry.name);
          if (entry.isDirectory()) {
            walkDataset(fullPath);
          } else if (entry.isFile()) {
            existing.add(path.basename(entry.name).toLowerCase());
          }
        }
      } catch {}
    };
    walkDataset(datasetRawDir);
  }

  return existing;
}

function appendCorrection(entry: CorrectionEntry): void {
  const correctionsPath = path.resolve('./dataset/corrections.jsonl');
  const line = JSON.stringify(entry) + '\n';
  fs.appendFileSync(correctionsPath, line, 'utf-8');
}

async function runRetrain(): Promise<void> {
  console.log('\n🔄 Auto-triggering classifier retraining from corrections...');
  const { spawn } = await import('child_process');

  return new Promise((resolve) => {
    const proc = spawn('bun', ['tools/retrain_classifier.ts'], {
      cwd: path.resolve('./'),
      stdio: 'inherit',
    });

    proc.on('close', () => {
      resolve();
    });

    proc.on('error', (err) => {
      console.error('   ❌ Retrain process error:', err.message);
      resolve();
    });
  });
}

async function interactiveHarvest() {
  const args = process.argv.slice(2);
  let targetFilter = '';
  let maxLimit = 50;
  let retrainThreshold = 50;
  let includeSkipped = false;
  let resetHistory = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--filter' && args[i + 1]) {
      targetFilter = args[i + 1]!.toLowerCase();
      i++;
    } else if (args[i] === '--limit' && args[i + 1]) {
      maxLimit = parseInt(args[i + 1]!, 10);
      i++;
    } else if (args[i] === '--all') {
      maxLimit = 999999;
    } else if (args[i] === '--retrain-threshold' && args[i + 1]) {
      retrainThreshold = parseInt(args[i + 1]!, 10);
      i++;
    } else if (args[i] === '--include-skipped') {
      includeSkipped = true;
    } else if (args[i] === '--reset-history') {
      resetHistory = true;
    }
  }

  if (resetHistory && fs.existsSync(HISTORY_PATH)) {
    fs.unlinkSync(HISTORY_PATH);
    console.log('🗑️  Harvest review history reset.');
  }

  console.log('\n=============================================================');
  console.log('🌾 GoaOnAuto Interactive Dataset Harvester (RTX 4060 GPU)');
  console.log('🎨 Raylib Dracula Confirmation GUI Enabled (1920x1080)');
  console.log(`📂 Scanning Work Directory: ${config.workDir}`);
  if (targetFilter) console.log(`🎯 Target Filter:          ${targetFilter}`);
  console.log(`🔢 Max Batch Limit:        ${maxLimit}`);
  console.log(`🔄 Retrain Threshold:       ${retrainThreshold} confirmed files`);
  console.log('=============================================================\n');

  // 1. Load persistent review history
  const historyMap = loadHarvestHistory();
  const alreadyReviewedCount = historyMap.size;

  // 2. Index work directory
  console.log('🔍 Indexing work directory subfolders...');
  const allFiles = getAllFilesRecursively(config.workDir);

  if (allFiles.length === 0) {
    console.log(`ℹ️  No files found in work directory: ${config.workDir}`);
    return;
  }

  // 3. Deduplicate against existing dataset and review history
  const existingFiles = getExistingDatasetFiles();
  let candidateFiles = allFiles.filter((f) => {
    if (!fs.existsSync(f)) return false;
    const normPath = f.toLowerCase();

    // Check if this exact file was already confirmed, changed, or skipped
    if (historyMap.has(normPath)) {
      const record = historyMap.get(normPath)!;
      if (!includeSkipped || record.decision !== 'skipped') {
        return false;
      }
    }

    const base = path.basename(f).toLowerCase();
    if (existingFiles.has(base)) return false;

    if (targetFilter) {
      return f.toLowerCase().includes(targetFilter);
    }
    return true;
  });

  console.log(`📁 Found ${allFiles.length} total work files:`);
  console.log(`   ⏮️  ${alreadyReviewedCount} previously reviewed / skipped files (bypassed)`);
  console.log(`   ✨ ${candidateFiles.length} new unharvested candidate documents available.\n`);

  if (candidateFiles.length === 0) {
    console.log('✅ All candidate documents in the work directory have already been reviewed!\n');
    console.log('👉 Tip: To re-process previously skipped files, run with --include-skipped\n');
    return;
  }

  const batchToProcess = candidateFiles.slice(0, maxLimit);
  console.log(`⚡ Processing ${batchToProcess.length} candidate documents via RTX 4060 GPU...\n`);

  // 4. Batch GPU OCR & Classification
  const startTime = Date.now();
  const batchResults = await processDocumentImagesBatch(batchToProcess);

  const stats: HarvestStats = {
    totalScanned: batchToProcess.length,
    confirmed: 0,
    changed: 0,
    skipped: 0,
    copiedToDataset: 0,
    categoryCounts: {},
  };

  const datasetRawDir = path.resolve('./dataset/raw');
  let confirmedSinceLastRetrain = 0;

  // 5. Interactive confirmation loop
  for (let i = 0; i < batchToProcess.length; i++) {
    const srcPath = batchToProcess[i]!;
    
    // Guard against deleted files
    if (!fs.existsSync(srcPath)) {
      console.log(`\n⚠️  File no longer exists, skipping: ${srcPath}`);
      continue;
    }

    const scanRes = batchResults[i];
    if (!scanRes) continue;

    const classRes = scanRes.classification;

    console.log(`\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`📄 [${i + 1}/${batchToProcess.length}] ${path.basename(srcPath)}`);
    console.log(`   🤖 AI Classification: ${classRes.docTypeName} (${classRes.docType}) — ${Math.round(classRes.confidence * 100)}%`);
    if (classRes.extractedName) {
      console.log(`   👤 Extracted Name: ${classRes.extractedName}`);
    }
    console.log(`   🎨 Opening Raylib Confirmation GUI...`);

    // 6. Spawn Raylib GUI for human verification
    const confirmRes: ConfirmationResult = await requestHumanConfirmation({
      filePath: srcPath,
      docType: classRes.docType,
      docTypeName: classRes.docTypeName,
      extractedName: classRes.extractedName,
      confidence: classRes.confidence,
    });

    // 7. Log the correction
    const correction: CorrectionEntry = {
      timestamp: new Date().toISOString(),
      filePath: srcPath,
      fileName: path.basename(srcPath),
      aiDetected: classRes.docType,
      aiDetectedName: classRes.docTypeName,
      aiConfidence: classRes.confidence,
      humanVerified: confirmRes.docType,
      humanVerifiedName: confirmRes.docTypeName,
      action: confirmRes.action as 'confirmed' | 'changed' | 'skipped',
      extractedName: confirmRes.extractedName || classRes.extractedName || '',
      customKeyword: confirmRes.customKeyword || '',
      matchedKeywords: classRes.matchedKeywords,
    };

    appendCorrection(correction);

    // 8. IMMEDIATELY update persistent history so this file is never re-prompted
    historyMap.set(srcPath.toLowerCase(), {
      filePath: srcPath,
      fileName: path.basename(srcPath),
      decision: confirmRes.action as 'confirmed' | 'changed' | 'skipped',
      docType: confirmRes.docType,
      timestamp: new Date().toISOString()
    });
    saveHarvestHistory(historyMap);

    if (confirmRes.customKeyword) {
      console.log(`   💡 Custom Training Keyword Learned: "${confirmRes.customKeyword}"`);
    }

    // 9. Handle result action
    if (confirmRes.action === 'skipped') {
      console.log(`   ⏭️  Skipped: ${path.basename(srcPath)} (Marked as reviewed, will not prompt again)`);
      stats.skipped++;
      continue;
    }

    const finalDocType = confirmRes.docType;
    const finalDocTypeName = confirmRes.docTypeName;

    if (confirmRes.action === 'changed') {
      console.log(`   ✏️  Category Corrected: ${classRes.docTypeName} → ${finalDocTypeName}`);
      stats.changed++;
    } else {
      console.log(`   ✅ Confirmed: ${finalDocTypeName}`);
      stats.confirmed++;
    }

    // 10. Copy to dataset/raw/<category>/
    if (!fs.existsSync(srcPath)) {
      console.log(`   ⚠️ Source file no longer exists, cannot copy: ${srcPath}`);
      continue;
    }

    const targetDir = path.join(datasetRawDir, finalDocType);
    fs.mkdirSync(targetDir, { recursive: true });

    const baseName = path.basename(srcPath);
    let targetPath = path.join(targetDir, baseName);

    // Handle filename collisions
    let counter = 1;
    const ext = path.extname(baseName);
    const stem = path.basename(baseName, ext);
    while (fs.existsSync(targetPath)) {
      targetPath = path.join(targetDir, `${stem}_${counter}${ext}`);
      counter++;
    }

    try {
      fs.copyFileSync(srcPath, targetPath);
      stats.copiedToDataset++;
      stats.categoryCounts[finalDocType] = (stats.categoryCounts[finalDocType] || 0) + 1;
      console.log(`   📥 Copied → dataset/raw/${finalDocType}/${path.basename(targetPath)}`);
    } catch (copyErr: any) {
      console.warn(`   ⚠️ Copy error: ${copyErr.message}`);
    }

    confirmedSinceLastRetrain++;

    // 11. Auto-trigger retrain after threshold
    if (confirmedSinceLastRetrain >= retrainThreshold) {
      await runRetrain();
      confirmedSinceLastRetrain = 0;
    }
  }

  // 12. Final summary
  const duration = Date.now() - startTime;

  console.log('\n=============================================================');
  console.log('🎉 INTERACTIVE HARVEST SUMMARY');
  console.log('=============================================================');
  console.log(`  📊 Total Scanned:       ${stats.totalScanned}`);
  console.log(`  ✅ Confirmed (as-is):    ${stats.confirmed}`);
  console.log(`  ✏️  Corrected by Human:   ${stats.changed}`);
  console.log(`  ⏭️  Skipped:              ${stats.skipped}`);
  console.log(`  📥 Copied to Dataset:    ${stats.copiedToDataset}`);
  console.log('-------------------------------------------------------------');

  for (const [type, count] of Object.entries(stats.categoryCounts)) {
    console.log(`  📁 ${type.padEnd(22)}: ${count} documents`);
  }

  console.log('-------------------------------------------------------------');
  console.log(`  ⏱️  Total Duration:       ${duration}ms`);
  console.log(`  📝 Review history saved to: dataset/harvest_history.json`);
  console.log('=============================================================\n');

  // Final retrain if there are remaining confirmed files
  if (confirmedSinceLastRetrain > 0 && stats.copiedToDataset >= 5) {
    console.log(`💡 ${confirmedSinceLastRetrain} new confirmed files since last retrain.`);
    console.log(`   Run "bun run retrain" to update classifier weights.\n`);
  }
}

interactiveHarvest();
