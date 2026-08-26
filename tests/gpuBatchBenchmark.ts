import * as path from 'path';
import * as fs from 'fs';
import { execSync } from 'child_process';
import { processDocumentImagesBatch } from '../src/scanner/documentScanner';

async function runBenchmark() {
  console.log('🏁 Starting GPU Batch Inference Benchmark on RTX 4060...\n');
  const testDir = path.resolve('./tests/mock_benchmark');
  fs.mkdirSync(testDir, { recursive: true });
  const sampleImage = path.join(testDir, 'sample_doc.jpg');
  const genScriptPath = path.join(testDir, 'gen_doc.py');

  if (!fs.existsSync(sampleImage)) {
    const genScript = `
import cv2
import numpy as np
import sys

img = np.full((600, 800, 3), 255, dtype=np.uint8)
cv2.putText(img, "GOVERNMENT OF INDIA", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
cv2.putText(img, "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
cv2.putText(img, "AADHAAR CARD - 5482 9102 3841", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
cv2.imwrite(sys.argv[1], img)
`;
    fs.writeFileSync(genScriptPath, genScript);
    execSync(`python "${genScriptPath}" "${sampleImage}"`, { stdio: 'pipe' });
  }

  const batchPaths = [sampleImage, sampleImage, sampleImage, sampleImage, sampleImage];

  console.log(`⚡ Warmup Batch (5 documents)...`);
  const t0 = Date.now();
  await processDocumentImagesBatch(batchPaths);
  console.log(`Warmup completed in ${Date.now() - t0} ms.\n`);

  console.log(`🔥 Warm GPU In-Memory Batch (5 documents)...`);
  const t1 = Date.now();
  const results = await processDocumentImagesBatch(batchPaths);
  const warmMs = Date.now() - t1;

  console.log(`\n✅ Warm Batch completed in ${warmMs} ms (~${Math.round(warmMs / batchPaths.length)} ms per image) on RTX 4060!`);
  console.log('Results summary:', results.map((r, i) => `[Doc ${i + 1}] Type: ${r.classification.docType}`));

  // Clean up benchmark temp files
  try {
    fs.rmSync(testDir, { recursive: true, force: true });
  } catch {}

  process.exit(0);
}

runBenchmark();
