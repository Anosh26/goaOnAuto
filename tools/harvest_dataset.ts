/**
 * Automated Dataset Harvester & Classifier.
 * Single Responsibility: Recursively scans work directory, classifies documents on RTX 4060 GPU, and auto-populates dataset/raw/.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';
import { config } from '../src/config';
import { processDocumentImagesBatch } from '../src/scanner/documentScanner';

const SUPPORTED_EXTS = new Set(['.jpg', '.jpeg', '.png', '.pdf', '.bmp', '.webp']);

function getFileHash(filePath: string): string {
  const buffer = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function getAllFilesRecursively(dir: string): string[] {
  let results: string[] = [];
  if (!fs.existsSync(dir)) return results;

  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === 'dataset' || entry.name.includes('Trash') || entry.name.toLowerCase().includes('temp') || entry.name.toLowerCase().includes('tmp')) {
          continue;
        }
        results = results.concat(getAllFilesRecursively(fullPath));
      } else if (entry.isFile()) {
        const lowerName = entry.name.toLowerCase();
        if (lowerName.startsWith('~$') || lowerName.startsWith('.') || lowerName.includes('.tmp') || lowerName.includes('.gui_preview') || lowerName.includes('.~lock') || lowerName.endsWith('.gdrive')) {
          continue;
        }
        const ext = path.extname(entry.name).toLowerCase();
        if (SUPPORTED_EXTS.has(ext)) {
          results.push(fullPath);
        }
      }
    }
  } catch {}
  return results;
}

async function harvestDataset() {
  const args = process.argv.slice(2);
  let targetFilter = '';
  let maxLimit = 100;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--filter' && args[i + 1]) {
      targetFilter = args[i + 1]!.toLowerCase();
      i++;
    } else if (args[i] === '--limit' && args[i + 1]) {
      maxLimit = parseInt(args[i + 1]!, 10);
      i++;
    } else if (args[i] === '--all') {
      maxLimit = 999999;
    }
  }

  console.log('\n=============================================================');
  console.log('🌾 GoaOnAuto Automated Dataset Harvester (RTX 4060 GPU)');
  console.log(`📂 Scanning Work Directory: ${config.workDir}`);
  if (targetFilter) console.log(`🎯 Target Filter:          ${targetFilter}`);
  console.log(`🔢 Max Batch Limit:        ${maxLimit}`);
  console.log('=============================================================\n');

  console.log('🔍 Indexing work directory subfolders...');
  let allFiles = getAllFilesRecursively(config.workDir);

  if (allFiles.length === 0) {
    console.log(`ℹ️  No files found in work directory: ${config.workDir}`);
    return;
  }

  console.log(`📁 Found ${allFiles.length} total files in Google Drive Work Directory.`);

  // Build index of existing file sizes & names in dataset/raw to quickly skip duplicates
  const existingFiles = new Set<string>();
  const datasetRawDir = path.resolve('./dataset/raw');

  if (fs.existsSync(datasetRawDir)) {
    const rawFiles = getAllFilesRecursively(datasetRawDir);
    for (const f of rawFiles) {
      existingFiles.add(path.basename(f).toLowerCase());
    }
  }

  // Filter candidate files
  let candidateFiles = allFiles.filter(f => {
    const base = path.basename(f).toLowerCase();
    if (existingFiles.has(base)) return false;
    if (targetFilter) {
      return f.toLowerCase().includes(targetFilter);
    }
    return true;
  });

  if (candidateFiles.length === 0) {
    console.log('✅ No new matching unharvested files found.\n');
    return;
  }

  const batchToProcess = candidateFiles.slice(0, maxLimit);
  console.log(`⚡ Processing ${batchToProcess.length} candidate documents via RTX 4060 GPU...\n`);

  const startTime = Date.now();
  const batchResults = await processDocumentImagesBatch(batchToProcess);

  const harvestedCounts: Record<string, number> = {};

  for (let i = 0; i < batchToProcess.length; i++) {
    const srcPath = batchToProcess[i]!;
    const res = batchResults[i];
    if (!res) continue;

    const docType = res.classification.docType;

    // If a filter was requested, only copy matches
    if (targetFilter && !docType.includes(targetFilter) && !targetFilter.includes(docType)) {
      continue;
    }

    const targetDir = path.join(datasetRawDir, docType);
    fs.mkdirSync(targetDir, { recursive: true });

    const baseName = path.basename(srcPath);
    let targetPath = path.join(targetDir, baseName);

    let counter = 1;
    const ext = path.extname(baseName);
    const stem = path.basename(baseName, ext);
    while (fs.existsSync(targetPath)) {
      targetPath = path.join(targetDir, `${stem}_${counter}${ext}`);
      counter++;
    }

    fs.copyFileSync(srcPath, targetPath);
    harvestedCounts[docType] = (harvestedCounts[docType] || 0) + 1;
    console.log(`   📥 [${docType.toUpperCase()}] ${path.basename(srcPath)} -> dataset/raw/${docType}/${path.basename(targetPath)}`);
  }

  const duration = Date.now() - startTime;
  const totalHarvested = Object.values(harvestedCounts).reduce((a, b) => a + b, 0);

  console.log('\n=============================================================');
  console.log('🎉 HARVEST SUMMARY');
  console.log('=============================================================');
  for (const [type, count] of Object.entries(harvestedCounts)) {
    console.log(`  📁 ${type.padEnd(20)}: ${count} documents added`);
  }
  console.log('-------------------------------------------------------------');
  console.log(`Total Harvested:    ${totalHarvested} documents`);
  console.log(`Processing Time:    ${duration}ms (~${batchToProcess.length > 0 ? Math.round(duration / batchToProcess.length) : 0} ms/doc)`);
  console.log('=============================================================\n');
}

harvestDataset();
