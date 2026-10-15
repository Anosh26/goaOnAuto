/**
 * Interactive OCR Quality Trainer & Field Ground-Truth Verification Runner.
 * Single Responsibility:
 * 1. Discovers document scans from target directory or dataset.
 * 2. Runs OCR extraction & demographic field deduction.
 * 3. Launches Raylib OCR Trainer GUI for human rating (1-5★) & field-by-field verification.
 * 4. Persists ground truth to dataset/ocr_corrections.jsonl & teaches ocr_spell_corrections.json.
 * 5. Auto-triggers classifier retraining and reports recognition benchmarks.
 */
import * as fs from 'fs';
import * as path from 'path';
import { spawn } from 'child_process';
import { config } from '../src/config';
import { processDocumentImagesBatch } from '../src/scanner/documentScanner';
import { GpuDaemonClient } from '../src/scanner/gpuDaemonClient';
import { classifyDocumentText } from '../src/classifier/documentClassifier';
import { ClassificationResult } from '../src/classifier/types';
import { synthesizeDossier, ExtractedDocument } from '../src/classifier/dossierExtractor';
import { applyOcrPostProcessing, recordSpellCorrection } from '../src/scanner/ocrPostProcessor';
import { OcrTrainerSession, requestOcrTrainingReview, OcrTrainerResult } from '../src/gui/ocrTrainerBridge';

const SUPPORTED_EXTS = new Set(['.jpg', '.jpeg', '.png', '.pdf', '.bmp', '.webp']);
const OCR_CORRECTIONS_FILE = path.resolve('./dataset/ocr_corrections.jsonl');
const CLASSIFIER_CORRECTIONS_FILE = path.resolve('./dataset/corrections.jsonl');

interface TrainerSessionStats {
  scanned: number;
  confirmed: number;
  skipped: number;
  ratings: number[];
  fieldsEditedCount: number;
  spellCorrectionsTaught: number;
}

function parseCliArgs(): { targetDir: string; singleFile?: string; autoRetrain: boolean } {
  const args = process.argv.slice(2);
  let targetDir = '';
  let singleFile: string | undefined;
  let autoRetrain = true;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (!arg) continue;
    if ((arg === '--dir' || arg === '-d') && args[i + 1]) {
      targetDir = args[++i]!;
    } else if ((arg === '--file' || arg === '-f') && args[i + 1]) {
      singleFile = args[++i]!;
    } else if (arg === '--no-retrain') {
      autoRetrain = false;
    } else if (!arg.startsWith('--') && !targetDir && !singleFile) {
      if (fs.existsSync(arg) && fs.statSync(arg).isFile()) {
        singleFile = arg;
      } else {
        targetDir = arg;
      }
    }
  }

  if (!targetDir && !singleFile) {
    // Default to current directory or dataset/samples
    const workDir = config.workDir;
    if (fs.existsSync(workDir) && fs.readdirSync(workDir).length > 0) {
      targetDir = workDir;
    } else if (fs.existsSync('./dataset/samples')) {
      targetDir = path.resolve('./dataset/samples');
    } else {
      targetDir = process.cwd();
    }
  }

  return { targetDir, singleFile, autoRetrain };
}

function discoverScans(targetDir: string): string[] {
  if (!fs.existsSync(targetDir)) return [];
  const files: string[] = [];

  const items = fs.readdirSync(targetDir, { withFileTypes: true });
  for (const item of items) {
    if (item.name.startsWith('.')) continue;
    const fullPath = path.join(targetDir, item.name);
    if (item.isDirectory()) {
      files.push(...discoverScans(fullPath));
    } else if (item.isFile()) {
      const ext = path.extname(item.name).toLowerCase();
      if (SUPPORTED_EXTS.has(ext) && !item.name.includes('.gui_prev')) {
        files.push(fullPath);
      }
    }
  }

  return files;
}

async function triggerClassifierRetrain(): Promise<void> {
  console.log('\n🧠 Auto-triggering classifier retraining from human feedback...');
  return new Promise((resolve) => {
    const proc = spawn('bun', ['tools/retrain_classifier.ts'], {
      cwd: config.projectRoot,
      stdio: 'inherit'
    });
    proc.on('close', (code) => {
      if (code === 0) {
        console.log('✅ Classifier weights successfully updated from human feedback!');
      } else {
        console.warn(`⚠️ Retraining exited with code ${code}`);
      }
      resolve();
    });
    proc.on('error', (err) => {
      console.error('❌ Failed to run retrain_classifier.ts:', err.message);
      resolve();
    });
  });
}

export async function runOcrTrainerCli(): Promise<void> {
  const { targetDir, singleFile, autoRetrain } = parseCliArgs();

  console.log('========================================================================');
  console.log('⭐ GOAONAUTO - INTERACTIVE OCR QUALITY TRAINER & EVALUATOR');
  console.log('========================================================================');

  const filesToReview: string[] = singleFile ? [path.resolve(singleFile)] : discoverScans(targetDir);

  if (filesToReview.length === 0) {
    console.log(`⚠️ No supported document scans found in: ${singleFile || targetDir}`);
    return;
  }

  console.log(`📂 Target Location:    ${singleFile || targetDir}`);
  console.log(`📄 Discovered Scans:   ${filesToReview.length} documents ready for evaluation`);
  console.log(`🖥️ Review Mode:        Persistent Fullscreen Raylib Desktop GUI (Single Window)`);
  console.log('------------------------------------------------------------------------\n');

  const stats: TrainerSessionStats = {
    scanned: 0,
    confirmed: 0,
    skipped: 0,
    ratings: [],
    fieldsEditedCount: 0,
    spellCorrectionsTaught: 0
  };

  const session = new OcrTrainerSession();
  await session.start();

  try {
    for (let idx = 0; idx < filesToReview.length; idx++) {
      const filePath = filesToReview[idx]!;
      const fileName = path.basename(filePath);
      stats.scanned++;

      console.log(`\n[${idx + 1}/${filesToReview.length}] 🔍 Running OCR on: ${fileName}...`);

      // 1. Run GPU OCR
      let rawOcrText = '';
      let rawOcrLines: string[] = [];
      let detectedClassification: ClassificationResult | null = null;

      try {
        const batchResults = await processDocumentImagesBatch([filePath]);
        const res = batchResults && batchResults.length > 0 ? batchResults[0] : null;
        if (res) {
          rawOcrText = res.rawText || '';
          rawOcrLines = rawOcrText.split(/\r?\n/).map((l: string) => l.trim()).filter(Boolean);
          detectedClassification = res.classification;
        }
      } catch (e: any) {
        console.warn(`   ⚠️ OCR processing warning for ${fileName}:`, e.message);
      }

      // 2. Apply Learned Spell-Corrections
      const postProcessedText = applyOcrPostProcessing(rawOcrText);

      // 3. Classify Document
      const classification = (detectedClassification && detectedClassification.docType !== 'document')
        ? detectedClassification
        : classifyDocumentText(postProcessedText, fileName, path.dirname(filePath));

      // Optional: Check for Aadhaar QR if it's an Aadhaar document
      let qrResult: any = null;
      if (classification.docType === 'aadhaar' || fileName.toLowerCase().includes('aadhaar')) {
        try {
          const daemon = GpuDaemonClient.getInstance();
          qrResult = await daemon.aadhaarQrScan(filePath);
        } catch {}
      }

      // 4. Extract Candidate Demographic Fields
      const mockDoc: ExtractedDocument = {
        docType: classification.docType,
        docTypeName: classification.docTypeName,
        rawText: postProcessedText,
        filePath: filePath,
        extractedName: classification.extractedName
      };
      const dossier = synthesizeDossier([mockDoc], qrResult);

      // Address extraction fallback if dossier has no address
      let extractedAddress = dossier.address?.value?.full || '';
      if (!extractedAddress && rawOcrLines.length > 0) {
        const addrCandidates = rawOcrLines.filter(l => 
          /(?:H\.?\s*No|House|Ward|Village|Goa|Margao|Panaji|Panjim|Mapusa|Ponda|Vasco|Tiswadi|Salcete|Bardez|403\d{3})/i.test(l)
        );
        if (addrCandidates.length > 0) {
          extractedAddress = addrCandidates.slice(0, 3).join(', ');
        }
      }

      const initialFields: Record<string, string | number> = {
        name: dossier.name?.value || classification.extractedName || '',
        dob: dossier.dob?.value || '',
        age: dossier.age?.value || '',
        aadhaar: dossier.aadhaar?.value || '',
        address: extractedAddress,
        prev_cert_no: dossier.previousResidenceCert?.number || '',
        years_in_goa: dossier.yearsInGoa?.value || 15
      };

      console.log(`   🏷️  AI Classification: ${classification.docTypeName} (${classification.docType})`);
      console.log(`   📜 Extracted OCR Lines: ${rawOcrLines.length} lines detected`);
      console.log(`   ⭐ Updating Raylib Trainer GUI [${idx + 1}/${filesToReview.length}]...`);

      // 5. Update Persistent Raylib Trainer GUI (no window re-creation)
      const userResult: OcrTrainerResult = await session.reviewDocument({
        filePath,
        docType: classification.docType,
        docTypeName: classification.docTypeName,
        confidence: 0.9,
        extractedFields: initialFields,
        rawOcrLines,
        docIndex: idx + 1,
        totalDocs: filesToReview.length
      });

      if (userResult.action === 'exit_session') {
        console.log(`\n🛑 Session closed by user. Exiting review loop.`);
        break;
      }

      if (userResult.action === 'skipped') {
        console.log(`   ⏭️ Skipped by user.`);
        stats.skipped++;
        continue;
      }

      if (userResult.action === 'confirmed') {
        stats.confirmed++;
        const userRating = userResult.rating || 5;
        stats.ratings.push(userRating);

      console.log(`   ★ User Rating: ${userRating}/5 Stars`);

      // Detect field edits
      const updatedFields = userResult.fields || {};
      let fieldEdits = 0;
      for (const [k, v] of Object.entries(updatedFields)) {
        if (String(v || '').trim() !== String(initialFields[k] || '').trim()) {
          fieldEdits++;
        }
      }
      if (fieldEdits > 0) {
        stats.fieldsEditedCount += fieldEdits;
        console.log(`   ✏️  Verified & corrected ${fieldEdits} demographic field(s).`);
      }

      // Record learned spell correction if provided
      if (userResult.spellCorrection) {
        const { original, corrected } = userResult.spellCorrection;
        if (original && corrected) {
          const taught = recordSpellCorrection(original, corrected);
          if (taught) {
            stats.spellCorrectionsTaught++;
            console.log(`   🔤 Learned new OCR word replacement: "${original}" ➔ "${corrected}"`);
          }
        }
      }

      // Append to dataset/ocr_corrections.jsonl
      const ocrEntry = {
        timestamp: new Date().toISOString(),
        filePath,
        fileName,
        rating: userRating,
        docType: userResult.docType || classification.docType,
        docTypeName: userResult.docTypeName || classification.docTypeName,
        aiDetected: classification.docType,
        extractedFields: initialFields,
        verifiedFields: updatedFields,
        spellCorrection: userResult.spellCorrection || null,
        rawOcrText
      };

      try {
        const ocrDir = path.dirname(OCR_CORRECTIONS_FILE);
        if (!fs.existsSync(ocrDir)) fs.mkdirSync(ocrDir, { recursive: true });
        fs.appendFileSync(OCR_CORRECTIONS_FILE, JSON.stringify(ocrEntry) + '\n', 'utf-8');
      } catch (err) {
        console.error('   ❌ Failed to append to ocr_corrections.jsonl:', err);
      }

      // Also append to classifier corrections.jsonl for retrain_classifier.ts
      const classifierEntry = {
        timestamp: new Date().toISOString(),
        filePath,
        fileName,
        aiDetected: classification.docType,
        aiDetectedName: classification.docTypeName,
        aiConfidence: 0.9,
        humanVerified: userResult.docType || classification.docType,
        humanVerifiedName: userResult.docTypeName || classification.docTypeName,
        action: userResult.docType === classification.docType ? 'confirmed' : 'changed',
        extractedName: updatedFields.name || classification.extractedName || '',
        matchedKeywords: classification.matchedKeywords
      };

      try {
        fs.appendFileSync(CLASSIFIER_CORRECTIONS_FILE, JSON.stringify(classifierEntry) + '\n', 'utf-8');
      } catch (err) {
        // non-fatal
      }
    }
  }
  } finally {
    await session.close();
  }

  // -------------------------------------------------------------
  // Summary & Retraining
  // -------------------------------------------------------------
  console.log('\n========================================================================');
  console.log('📈 OCR EVALUATION & TRAINING SUMMARY');
  console.log('========================================================================');
  console.log(`Total Documents Scanned:        ${stats.scanned}`);
  console.log(`Confirmed & Rated:              ${stats.confirmed}`);
  console.log(`Skipped:                        ${stats.skipped}`);

  const avgRating = stats.ratings.length > 0
    ? (stats.ratings.reduce((a, b) => a + b, 0) / stats.ratings.length).toFixed(1)
    : 'N/A';

  console.log(`Average OCR Quality Score:      ${avgRating} / 5.0 ⭐`);
  console.log(`Demographic Fields Corrected:   ${stats.fieldsEditedCount}`);
  console.log(`New Spell Corrections Taught:   ${stats.spellCorrectionsTaught}`);
  console.log('------------------------------------------------------------------------');

  if (autoRetrain && (stats.confirmed > 0 || stats.spellCorrectionsTaught > 0)) {
    await triggerClassifierRetrain();
  } else {
    console.log('\n💡 You can manually retrain classifier weights at any time with:');
    console.log('   bun run data:retrain\n');
  }
}

// Auto-run when executed directly
if (require.main === module || process.argv[1]?.includes('runOcrTrainer')) {
  runOcrTrainerCli().catch(err => {
    console.error('Fatal OCR Trainer error:', err);
    process.exit(1);
  });
}
