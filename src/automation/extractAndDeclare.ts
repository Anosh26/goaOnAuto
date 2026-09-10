/**
 * Automated Document Extraction & Declaration Pipeline Runner.
 * Single Responsibility:
 * 1. Shows real-time Raylib GPU progress level monitor.
 * 2. Scans folder files, runs GPU OCR and Aadhaar QR Golden Source decoding.
 * 3. Synthesizes applicant_dossier.json (with exact calculated age from DOB).
 * 4. Gracefully terminates progress monitor and transitions into declaration_app.py prefilled.
 */
import * as path from 'path';
import * as fs from 'fs';
import { spawn } from 'child_process';
import { config } from '../config';
import { ProgressBridge } from '../gui/progressBridge';
import { GpuDaemonClient, AadhaarQrResult } from '../scanner/gpuDaemonClient';
import { processDocumentImagesBatch } from '../scanner/documentScanner';
import { synthesizeDossier, ExtractedDocument, calculateAgeFromDob } from '../classifier/dossierExtractor';

interface CliArgs {
  type: 'residence' | 'obc' | 'divergence' | 'photo' | 'bg_remover';
  dir: string;
}

function parseArgs(): CliArgs {
  const args = process.argv.slice(2);
  let type: 'residence' | 'obc' | 'divergence' | 'photo' | 'bg_remover' = 'residence';
  let dir = '';

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--type' && args[i + 1]) {
      const raw = args[++i].toLowerCase();
      if (raw === 'obc' || raw === 'divergence' || raw === 'residence' || raw === 'photo' || raw === 'bg_remover') {
        type = raw as any;
      }
    } else if (arg === '--dir' && args[i + 1]) {
      dir = args[++i];
    } else if (!arg.startsWith('--') && !dir) {
      dir = arg;
    }
  }

  let resolvedDir = dir ? path.resolve(dir) : path.resolve(process.cwd());
  if (fs.existsSync(resolvedDir) && fs.statSync(resolvedDir).isFile()) {
    if (type !== 'photo' && type !== 'bg_remover') {
      resolvedDir = path.dirname(resolvedDir);
    }
  }
  return { type, dir: resolvedDir };
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function runExtractAndDeclare(): Promise<void> {
  const { type, dir } = parseArgs();

  // If photo / bg_remover mode, launch Background Removal GUI directly
  if (type === 'photo' || type === 'bg_remover') {
    launchBgRemover(dir);
    return;
  }

  console.log(`\n=============================================================`);
  console.log(`🚀 GoaOnAuto - Automated Declaration Pipeline`);
  console.log(`   Type:      ${type.toUpperCase()}`);
  console.log(`   Folder:    ${dir}`);
  console.log(`=============================================================\n`);

  if (!fs.existsSync(dir)) {
    console.error(`❌ Error: Target directory does not exist: ${dir}`);
    process.exit(1);
  }

  // 1. Initialize Raylib GPU Progress Level Monitor
  const progress = ProgressBridge.getInstance();
  progress.ensureRunning();

  progress.update({
    status: `Starting automated scan for ${type.toUpperCase()}...`,
    current_file: path.basename(dir),
    progress_percent: 5,
    queue_length: 1
  });

  await sleep(400);

  // 2. Discover document images & PDFs in target folder
  const candidateExtensions = ['.jpg', '.jpeg', '.png', '.pdf'];
  const ignoredFiles = [
    'residence_declaration.pdf', 'residence_declaration.tex',
    'obc_declaration.pdf', 'obc_declaration.tex',
    'divergence_declaration.pdf', 'divergence_declaration.tex',
    'applicant_dossier.json', 'residence_form_data.json',
    'obc_form_data.json', 'divergence_form_data.json'
  ];

  const entries = fs.readdirSync(dir);
  const candidateFiles = entries
    .filter((file) => {
      const lower = file.toLowerCase();
      const ext = path.extname(lower);
      return candidateExtensions.includes(ext) && !ignoredFiles.includes(lower);
    })
    .map((file) => path.join(dir, file));

  console.log(`📂 Found ${candidateFiles.length} candidate documents in folder.`);

  if (candidateFiles.length === 0) {
    console.log(`ℹ️ No scanned images or PDFs found. Launching declaration GUI directly.`);
    progress.update({
      status: 'No raw scan documents found. Launching Declaration form...',
      current_file: path.basename(dir),
      progress_percent: 100
    });
    await sleep(800);
    progress.stop();
    launchDeclarationApp(type, dir);
    return;
  }

  // 3. Run GPU OCR batch processing
  progress.update({
    status: `⚡ GPU OCR Analyzing ${candidateFiles.length} documents...`,
    current_file: path.basename(candidateFiles[0]),
    progress_percent: 25,
    queue_length: candidateFiles.length
  });

  const batchResults = await processDocumentImagesBatch(candidateFiles);

  progress.update({
    status: `Classified ${batchResults.length} documents. Checking Golden Source...`,
    current_file: 'Document Classification',
    progress_percent: 60,
    queue_length: candidateFiles.length
  });

  const extractedDocs: ExtractedDocument[] = batchResults.map((res) => ({
    docType: res.classification.docType,
    docTypeName: res.classification.docTypeName,
    rawText: res.rawText || '',
    filePath: res.newPath || res.imagePath,
    extractedName: res.classification.extractedName
  }));

  // 4. Decode Aadhaar QR Code if Aadhaar document is found
  let qrResult: AadhaarQrResult | null = null;
  const aadhaarDoc = extractedDocs.find((d) => d.docType === 'aadhaar');
  if (aadhaarDoc) {
    progress.update({
      status: `🔍 Decoding Aadhaar QR Golden Source...`,
      current_file: path.basename(aadhaarDoc.filePath),
      progress_percent: 75
    });

    console.log(`   🔍 Scanning Aadhaar QR code for ${path.basename(aadhaarDoc.filePath)}...`);
    const daemon = GpuDaemonClient.getInstance();
    qrResult = await daemon.aadhaarQrScan(aadhaarDoc.filePath);

    if (qrResult && qrResult.success) {
      console.log(`   ✅ Aadhaar QR Decode Success: Found ${qrResult.name} (DOB: ${qrResult.dob || 'N/A'})`);
    } else {
      console.log(`   ⚠️ Aadhaar QR not found or could not be decoded. Using OCR fallback.`);
    }
  }

  // 5. Synthesize Dossier & compute exact age from DOB
  progress.update({
    status: `Synthesizing Dossier & calculating person age...`,
    current_file: 'applicant_dossier.json',
    progress_percent: 90
  });

  const dossier = synthesizeDossier(extractedDocs, qrResult);

  // If dossier has DOB but no age, compute it
  if (dossier.dob && dossier.dob.value && (!dossier.age || !dossier.age.value)) {
    const calculatedAge = calculateAgeFromDob(dossier.dob.value);
    if (calculatedAge !== undefined) {
      dossier.age = {
        value: calculatedAge,
        confidence: 1.0,
        sourceDoc: 'Calculated from DOB'
      };
    }
  }

  const dossierPath = path.join(dir, 'applicant_dossier.json');
  fs.writeFileSync(dossierPath, JSON.stringify(dossier, null, 2), 'utf-8');
  console.log(`   📄 Saved synthesized Applicant Dossier: ${dossierPath}`);
  if (dossier.dob?.value) {
    console.log(`   🎂 Extracted DOB: ${dossier.dob.value} | Calculated Age: ${dossier.age?.value || 'N/A'}`);
  }

  // 6. Complete progress display and transition to Declaration App
  progress.update({
    status: `✅ OCR & Extraction Complete! Launching ${type.toUpperCase()} Declaration...`,
    current_file: 'Ready',
    progress_percent: 100,
    queue_length: 0
  });

  await sleep(1000);
  progress.stop();

  launchDeclarationApp(type, dir);
}

function launchBgRemover(dirOrFile: string): void {
  const scriptPath = path.join(config.pythonDir, 'gui', 'bg_remover_gui.py');
  console.log(`🎨 Launching Background Remover GUI: ${scriptPath}`);

  const child = spawn(config.pythonBin, [scriptPath, dirOrFile], {
    cwd: config.projectRoot,
    windowsHide: false,
    stdio: 'inherit'
  });

  child.on('error', (err) => {
    console.error('Failed to launch Background Remover:', err);
  });
}

function launchDeclarationApp(type: string, dir: string): void {
  const scriptPath = path.join(config.pythonDir, 'gui', 'declaration_app.py');
  console.log(`🚀 Launching Declaration App GUI: ${scriptPath}`);

  const child = spawn(config.pythonBin, [scriptPath, '--type', type, '--dir', dir], {
    cwd: config.projectRoot,
    windowsHide: false,
    stdio: 'inherit'
  });

  child.on('error', (err) => {
    console.error('Failed to launch Declaration App:', err);
  });
}

if (import.meta.main || require.main === module) {
  runExtractAndDeclare().catch((err) => {
    console.error('Extraction error:', err);
    process.exit(1);
  });
}
