/**
 * Ground-Truth Dataset Accuracy & Precision Evaluator.
 * Single Responsibility: Evaluates OCR & Classifier accuracy across ground-truth files in dataset/raw/ and dataset/samples/.
 */
import * as fs from 'fs';
import * as path from 'path';
import { processDocumentImagesBatch } from '../src/scanner/documentScanner';

interface EvalResult {
  category: string;
  total: number;
  correct: number;
  accuracy: number;
  failures: Array<{
    filePath: string;
    expected: string;
    detected: string;
    confidence: number;
    extractedName?: string;
  }>;
}

const SUPPORTED_EXTS = new Set(['.jpg', '.jpeg', '.png', '.pdf', '.bmp', '.webp']);

async function evaluateDataset() {
  console.log('\n=============================================================');
  console.log('📊 GoaOnAuto Ground-Truth Dataset Evaluator (RTX 4060 GPU)');
  console.log('=============================================================\n');

  const rootDatasetDirs = [
    path.resolve('./dataset/raw'),
    path.resolve('./dataset/samples')
  ];

  const categoryMap = new Map<string, string[]>();

  for (const baseDir of rootDatasetDirs) {
    if (!fs.existsSync(baseDir)) continue;

    const subDirs = fs.readdirSync(baseDir, { withFileTypes: true });
    for (const sub of subDirs) {
      if (!sub.isDirectory()) continue;
      const catName = sub.name;
      const catPath = path.join(baseDir, catName);

      const files = fs.readdirSync(catPath)
        .filter(f => SUPPORTED_EXTS.has(path.extname(f).toLowerCase()))
        .map(f => path.join(catPath, f));

      if (files.length > 0) {
        const existing = categoryMap.get(catName) || [];
        categoryMap.set(catName, existing.concat(files));
      }
    }
  }

  if (categoryMap.size === 0) {
    console.log('ℹ️  No dataset files found in dataset/raw/ or dataset/samples/.');
    console.log('👉 To start evaluating accuracy:');
    console.log('   Copy your sample documents into: dataset/raw/<doc_category>/\n');
    console.log('   Example categories:');
    console.log('   - dataset/raw/aadhaar/');
    console.log('   - dataset/raw/residence_cert/');
    console.log('   - dataset/raw/passport_photo/');
    console.log('   - dataset/raw/pan/');
    console.log('   - dataset/raw/voter_id/\n');
    return;
  }

  let totalDocs = 0;
  let totalCorrect = 0;
  const evalResults: EvalResult[] = [];
  const startTime = Date.now();

  for (const [catName, filePaths] of categoryMap.entries()) {
    console.log(`🔍 Evaluating Category [${catName}] (${filePaths.length} documents)...`);
    const batchResults = await processDocumentImagesBatch(filePaths);

    let correct = 0;
    const failures: EvalResult['failures'] = [];

    for (let i = 0; i < filePaths.length; i++) {
      const filePath = filePaths[i]!;
      const scanRes = batchResults[i];
      const detectedType = scanRes ? scanRes.classification.docType : 'unknown';
      const confidence = scanRes ? scanRes.classification.confidence : 0;
      const extractedName = scanRes ? scanRes.classification.extractedName : undefined;

      if (detectedType === catName) {
        correct++;
      } else {
        failures.push({
          filePath,
          expected: catName,
          detected: detectedType,
          confidence,
          extractedName
        });
      }
    }

    const accuracy = filePaths.length > 0 ? (correct / filePaths.length) * 100 : 0;
    totalDocs += filePaths.length;
    totalCorrect += correct;

    evalResults.push({
      category: catName,
      total: filePaths.length,
      correct,
      accuracy,
      failures
    });
  }

  const durationMs = Date.now() - startTime;
  const overallAccuracy = totalDocs > 0 ? (totalCorrect / totalDocs) * 100 : 0;

  console.log('\n=============================================================');
  console.log('📈 ACCURACY SCOREBOARD');
  console.log('=============================================================');
  console.log(`${'Category'.padEnd(25)} | ${'Tested'.padStart(8)} | ${'Passed'.padStart(8)} | ${'Accuracy'.padStart(10)}`);
  console.log('-------------------------------------------------------------');

  for (const res of evalResults) {
    const accStr = `${res.accuracy.toFixed(1)}%`;
    console.log(`${res.category.padEnd(25)} | ${String(res.total).padStart(8)} | ${String(res.correct).padStart(8)} | ${accStr.padStart(10)}`);
  }

  console.log('=============================================================');
  console.log(`Total Documents:    ${totalDocs}`);
  console.log(`Total Correct:      ${totalCorrect}`);
  console.log(`Overall Accuracy:   ${overallAccuracy.toFixed(2)}%`);
  console.log(`Total Duration:     ${durationMs}ms (~${Math.round(durationMs / totalDocs)} ms/doc)`);
  console.log('=============================================================\n');

  // Print failures if any
  const allFailures = evalResults.flatMap(r => r.failures);
  if (allFailures.length > 0) {
    console.log(`⚠️  ${allFailures.length} Misclassified Documents to Inspect:`);
    for (const f of allFailures) {
      console.log(`  ❌ ${path.basename(f.filePath)}`);
      console.log(`     Expected: ${f.expected} | Detected: ${f.detected} (${Math.round(f.confidence * 100)}%)`);
      if (f.extractedName) {
        console.log(`     Extracted Name: ${f.extractedName}`);
      }
    }
    console.log('');
  } else {
    console.log('🎉 100% Accuracy across all tested dataset documents!\n');
  }
}

evaluateDataset();
