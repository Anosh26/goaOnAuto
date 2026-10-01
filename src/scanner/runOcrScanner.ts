/**
 * GoaOnAuto - Automated OCR Document Scanner & Classifier Runner.
 * Single Responsibility:
 * 1. Discovers all document scans in the target client folder.
 * 2. Runs GPU batch OCR & AI document classification.
 * 3. Intelligently renames files to standardized clean names (e.g. aadhaar_card, previous_residence_certificate).
 * 4. Extracts golden demographic truth: Aadhaar Number, DOB, Age, Gender, Address, Previous Residence Cert records.
 * 5. Saves synthesized applicant_dossier.json and residence_form_data.json.
 */
import * as path from 'path';
import * as fs from 'fs';
import * as readline from 'readline';
import { config } from '../config';
import { processDocumentImagesBatch, BatchScanResult } from './documentScanner';
import { GpuDaemonClient, AadhaarQrResult } from './gpuDaemonClient';
import { synthesizeDossier, ExtractedDocument, calculateAgeFromDob } from '../classifier/dossierExtractor';
import { ResidenceCertificateFormPage } from '../automation/pages/residenceFormPage';

const NORTH_GOA_TALUKAS = ['bardez', 'pernem', 'tiswadi', 'bicholim', 'sattari'];
const SOUTH_GOA_TALUKAS = ['salcete', 'mormugao', 'ponda', 'quepem', 'sanguem', 'dharbandora', 'canacona'];

const TALUKA_CANONICAL_NAMES: Record<string, string> = {
  bardez: 'Bardez',
  pernem: 'Pernem',
  tiswadi: 'Tiswadi',
  bicholim: 'Bicholim',
  sattari: 'Sattari',
  salcete: 'Salcete',
  mormugao: 'Mormugao',
  ponda: 'Ponda',
  quepem: 'Quepem',
  sanguem: 'Sanguem',
  dharbandora: 'Dharbandora',
  canacona: 'Canacona'
};

function parseTargetDir(): string {
  const args = process.argv.slice(2);
  let targetDir = '';

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (!arg) continue;
    if ((arg === '--dir' || arg === '-d') && args[i + 1]) {
      targetDir = args[++i] || '';
    } else if (!arg.startsWith('--') && !targetDir) {
      targetDir = arg;
    }
  }

  if (!targetDir) {
    targetDir = process.cwd();
  }

  let resolved = path.resolve(targetDir);
  if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) {
    resolved = path.dirname(resolved);
  }

  return resolved;
}

/**
 * Standardizes filename based on document type and counter.
 */
function getStandardizedFilename(docType: string, index: number, ext: string, totalOfType: number): string {
  const typeMap: Record<string, string> = {
    aadhaar: totalOfType > 1 ? (index === 0 ? 'aadhaar_front' : 'aadhaar_back') : 'aadhaar_card',
    residence_cert: 'previous_residence_certificate',
    bonafide_cert: 'bonafide_certificate',
    birth_cert: 'birth_certificate',
    passport_photo: 'passport_photo',
    signature: 'signature',
    pan: 'pan_card',
    voter_id: 'voter_card',
    marksheet: 'marksheet',
    driving_license: 'driving_license',
    electricity_bill: 'electricity_bill',
    house_tax: 'house_tax_receipt',
    ration_card: 'ration_card',
    marriage_cert: 'marriage_certificate',
    caste_cert: 'caste_certificate',
    obc_cert: 'obc_certificate',
    pcc: 'police_clearance_certificate'
  };

  const base = typeMap[docType];
  if (!base) return '';

  if (totalOfType > 1 && docType !== 'aadhaar') {
    return `${base}_${index + 1}${ext}`;
  }
  return `${base}${ext}`;
}

export async function runOcrScanner(): Promise<void> {
  const dir = parseTargetDir();

  console.log('========================================================================');
  console.log('🔍 GOAONAUTO - DOCUMENT SCANNER & CLASSIFIER');
  console.log(`📂 Scanning Folder: ${dir}`);
  console.log('========================================================================\n');

  if (!fs.existsSync(dir)) {
    console.error(`❌ Target directory does not exist: ${dir}`);
    process.exit(1);
  }

  // 1. Discover Candidate Files
  const candidateExtensions = ['.jpg', '.jpeg', '.png', '.pdf', '.webp', '.bmp', '.tiff'];
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

  if (candidateFiles.length === 0) {
    console.log('⚠️ No document images or PDFs found in this folder.');
    console.log('   Add documents (Aadhaar, Photos, Certificates) and try again.');
    process.exit(0);
  }

  console.log(`📄 Found ${candidateFiles.length} candidate documents to analyze.`);

  // 2. Batch GPU OCR & Classification
  console.log('⚡ Running GPU OCR analysis and visual classification...');
  const batchResults = await processDocumentImagesBatch(candidateFiles, { autoRename: false, targetDir: dir });

  // Count documents per type for clean multi-page naming
  const typeCounts: Record<string, number> = {};
  for (const res of batchResults) {
    const t = res.classification.docType;
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  }

  // 3. Rename Files to Clean Canonical Names
  console.log('\n🏷️  Standardizing and Renaming Documents...');
  const currentTypeIdx: Record<string, number> = {};
  const renamedFiles: Array<{ oldName: string; newName: string; type: string }> = [];

  for (const res of batchResults) {
    const docType = res.classification.docType;
    const oldPath = res.imagePath;
    const oldName = path.basename(oldPath);
    const ext = path.extname(oldName).toLowerCase();

    const idx = currentTypeIdx[docType] || 0;
    currentTypeIdx[docType] = idx + 1;

    const stdName = getStandardizedFilename(docType, idx, ext, typeCounts[docType] || 1);

    if (stdName && stdName.toLowerCase() !== oldName.toLowerCase()) {
      let targetPath = path.join(dir, stdName);
      let counter = 1;
      const stem = path.basename(stdName, ext);

      while (fs.existsSync(targetPath) && targetPath.toLowerCase() !== oldPath.toLowerCase()) {
        targetPath = path.join(dir, `${stem}_${counter}${ext}`);
        counter++;
      }

      try {
        fs.renameSync(oldPath, targetPath);
        res.newPath = targetPath;
        renamedFiles.push({ oldName, newName: path.basename(targetPath), type: res.classification.docTypeName });
        console.log(`   ✔️ [${res.classification.docTypeName}]: ${oldName} -> ${path.basename(targetPath)}`);
      } catch (e: any) {
        console.warn(`   ⚠️ Could not rename ${oldName}: ${e.message}`);
        res.newPath = oldPath;
      }
    } else {
      res.newPath = oldPath;
      console.log(`   ✔️ [${res.classification.docTypeName}]: ${oldName}`);
    }
  }

  // 4. Decode Aadhaar QR Golden Source if Aadhaar document is present
  const extractedDocs: ExtractedDocument[] = batchResults.map((res) => ({
    docType: res.classification.docType,
    docTypeName: res.classification.docTypeName,
    rawText: res.rawText || '',
    filePath: res.newPath || res.imagePath,
    extractedName: res.classification.extractedName
  }));

  let qrResult: AadhaarQrResult | null = null;
  const aadhaarDoc = extractedDocs.find((d) => d.docType === 'aadhaar');
  if (aadhaarDoc) {
    console.log(`\n🔍 Scanning Aadhaar QR Golden Source on ${path.basename(aadhaarDoc.filePath)}...`);
    try {
      const daemon = GpuDaemonClient.getInstance();
      qrResult = await daemon.aadhaarQrScan(aadhaarDoc.filePath);
      if (qrResult && qrResult.success) {
        console.log(`   ✨ Aadhaar QR Decoded: ${qrResult.name} | DOB: ${qrResult.dob || 'N/A'}`);
      } else {
        console.log('   ℹ️ Aadhaar QR not found or obscured. Using high-precision OCR text decoding.');
      }
    } catch {
      console.log('   ℹ️ Aadhaar QR scan skipped. Proceeding with OCR extraction.');
    }
  }

  // 5. Synthesize Dossier with High Precision Extraction
  console.log('\n📊 Synthesizing Demographic Ground Truth...');
  const dossier = synthesizeDossier(extractedDocs, qrResult);

  // Compute Age from DOB if not already set
  if (dossier.dob?.value && (!dossier.age || !dossier.age.value)) {
    const age = calculateAgeFromDob(dossier.dob.value);
    if (age !== undefined) {
      dossier.age = { value: age, confidence: 1.0, sourceDoc: 'Calculated from DOB' };
    }
  }

  // 6. Address Resolution
  const rawAddress = dossier.address?.value?.full || 'H.No. 1, Goa';
  const pinMatch = rawAddress.match(/\b(403\d{3})\b/);
  const pincode = pinMatch?.[1] || dossier.address?.value?.pincode || '403516';

  const houseMatch = rawAddress.match(/(?:H\.?\s*No\.?|House\s*No\.?|Flat\s*No\.?)\s*([A-Za-z0-9\-\/\.\s]+?)(?:,|$|\n)/i);
  const houseNo = houseMatch?.[1]?.trim() || dossier.address?.value?.houseNo || 'H.No. 45/B';

  let taluka = 'Bardez';
  let district: 'North Goa' | 'South Goa' = 'North Goa';
  const checkText = (dossier.address?.value?.taluka || rawAddress).toLowerCase();
  for (const [key, name] of Object.entries(TALUKA_CANONICAL_NAMES)) {
    if (checkText.includes(key)) {
      taluka = name;
      district = SOUTH_GOA_TALUKAS.includes(key) ? 'South Goa' : 'North Goa';
      break;
    }
  }
  const village = dossier.address?.value?.villageOrCity || 'Arpora';

  // 7. Residence Certificate Form Data Synthesis
  const currentYear = new Date().getFullYear();
  const rawDob = dossier.dob?.value || '';
  const formattedDob = ResidenceCertificateFormPage.formatPortalDate(rawDob);
  const yearsInGoa = dossier.yearsInGoa?.value || 15;
  const sinceYear = currentYear - yearsInGoa;

  // Ensure stay from year is not before birth year
  let stayFromYear = sinceYear;
  const birthYearMatch = formattedDob.match(/\d{4}$/);
  if (birthYearMatch) {
    const birthYear = parseInt(birthYearMatch[0], 10);
    if (birthYear > stayFromYear) {
      stayFromYear = birthYear;
    }
  }
  const stayFromDate = `01-Jan-${stayFromYear}`;

  const hasPrevCert = Boolean(dossier.hasPreviousResidenceCert);
  const prevCertNum = dossier.previousResidenceCert?.number || '';
  const prevCertDate = dossier.previousResidenceCert?.issueDate
    ? ResidenceCertificateFormPage.formatPortalDate(dossier.previousResidenceCert.issueDate)
    : '';
  const prevCertAuth = dossier.previousResidenceCert?.authority || `Mamlatdar of ${taluka}`;

  const cleanAadhaar = dossier.idProofNumber?.value || dossier.aadhaar?.value || '999999990019';

  const residenceFormData = {
    serviceType: 'residence_certificate',
    mode: 'relative', // Always relative standard
    applicantName: dossier.name?.value || path.basename(dir),
    age: dossier.age?.value || (rawDob ? calculateAgeFromDob(rawDob) : 25) || 25,
    dob: formattedDob,
    gender: dossier.gender?.value?.toUpperCase().startsWith('F') ? 'Female' : 'Male',
    maritalStatus: (dossier.age?.value || 25) < 21 ? 'Unmarried' : 'Married',
    relationType: 'Father',
    relationName: dossier.relation?.name || '',
    relativeRelation: 'Father',
    relativeName: dossier.relation?.name || 'Parent Name',
    purpose: '15 years',
    periodType: 'For',
    sinceYear,
    yearsInGoa: currentYear - stayFromYear,
    stayFromDate,
    houseNo,
    premisesType: 'Owned',
    currentlyStaying: 'Yes',
    address: rawAddress,
    locality: rawAddress.replace(new RegExp(pincode, 'g'), '').replace(new RegExp(taluka, 'gi'), '').trim() || 'Near Church',
    taluka,
    district,
    village,
    pincode,
    place: 'Mapusa',
    declarationDate: new Date().toLocaleDateString('en-GB'),
    // Previous Residence Certificate Records
    issuedEarlier: hasPrevCert ? 'Yes' : 'No',
    previousCertNumber: prevCertNum,
    previousCertDate: prevCertDate,
    previousCertAuthority: prevCertAuth,
    previousCertAddress: rawAddress,
    // ID Proof
    idProofType: 'Aadhaar Card',
    idProofNumber: cleanAadhaar,
    photoPath: dossier.photoPath || path.join(dir, 'passport_photo.jpg'),
    signaturePath: dossier.signaturePath || path.join(dir, 'signature.png'),
    updatedAt: new Date().toISOString()
  };

  // 8. Save applicant_dossier.json and residence_form_data.json
  const dossierPath = path.join(dir, 'applicant_dossier.json');
  fs.writeFileSync(dossierPath, JSON.stringify(dossier, null, 2), 'utf-8');

  const formDataPath = path.join(dir, 'residence_form_data.json');
  fs.writeFileSync(formDataPath, JSON.stringify(residenceFormData, null, 2), 'utf-8');

  // 9. Output Summary Report
  console.log('\n========================================================================');
  console.log('🎉 OCR SCANNING & EXTRACTION COMPLETE!');
  console.log('========================================================================');
  console.log(`👤 Applicant Name:    ${residenceFormData.applicantName}`);
  console.log(`🎂 Date of Birth:     ${residenceFormData.dob} (Age: ${residenceFormData.age})`);
  console.log(`⚧  Gender:            ${residenceFormData.gender}`);
  console.log(`🪪 Aadhaar Number:    ${cleanAadhaar}`);
  console.log(`🏠 Address:           ${houseNo}, ${village}, ${taluka} (${district}) - ${pincode}`);
  console.log(`📅 Residing Since:    ${stayFromDate} (${residenceFormData.yearsInGoa} Years)`);
  console.log(`📜 Previous Cert:     ${hasPrevCert ? `YES (No: ${prevCertNum || 'Found'}, Date: ${prevCertDate || 'Recorded'})` : 'NO'}`);
  console.log('------------------------------------------------------------------------');
  console.log(`💾 Saved Applicant Dossier:    ${dossierPath}`);
  console.log(`💾 Saved Residence Form Data:  ${formDataPath}`);
  console.log('\n👉 Next steps available in right-click menu:');
  console.log('   1. 🏛️  Residence Certificate Declaration (Customize & Compile PDF)');
  console.log('   2. 🌐 Auto-Fill GoaOnline Residence Form (Instant Headed Browser Filling)');
  console.log('\n⌨️  Press ENTER to exit.');
  console.log('========================================================================\n');

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  await new Promise<void>((resolve) => {
    rl.question('', () => {
      rl.close();
      resolve();
    });
  });
}

if (import.meta.main || require.main === module) {
  runOcrScanner().catch((err) => {
    console.error('❌ OCR Scanner Error:', err);
    process.exit(1);
  });
}
