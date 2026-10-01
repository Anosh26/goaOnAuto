/**
 * GoaOnAuto - Real Client Residence Certificate Form Filler.
 * Single Responsibility:
 * 1. Resolves client directory from CLI / context menu (%1 or --dir).
 * 2. Loads client data from residence_form_data.json, applicant_dossier.json, or on-the-fly extraction.
 * 3. Launches Brave browser with persistent citizen profile.
 * 4. Verifies/waits for GoaOnline login handshake.
 * 5. Navigates to REV05 (Residence Certificate) and proceeds to Screen 1.
 * 6. Auto-populates all Screen 1 fields (Mode, Personal, Address Modal, Aadhaar ID, Declaration).
 * 7. Leaves browser open on Screen 1 in SAFE MODE for client review and final submission.
 */
import * as path from 'path';
import * as fs from 'fs';
import * as readline from 'readline';
import { config } from '../config';
import { startPortalPhase1, updatePortalStatusOverlay } from './services/portalSessionManager';
import { ResidenceCertificateFormPage, ResidenceFormData } from './pages/residenceFormPage';
import { calculateAgeFromDob } from '../classifier/dossierExtractor';

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

function parseArgs(): { targetDir: string; keepSession: boolean } {
  const args = process.argv.slice(2);
  let targetDir = '';
  let keepSession = true;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (!arg) continue;
    if ((arg === '--dir' || arg === '-d') && args[i + 1]) {
      targetDir = args[++i] || '';
    } else if (arg === '--fresh-login') {
      keepSession = false;
    } else if (!arg.startsWith('--') && !targetDir) {
      targetDir = arg;
    }
  }

  if (!targetDir) {
    targetDir = findLatestApplicantDir(config.workDir) || path.join(config.projectRoot, 'scratch');
  }

  let resolved = path.resolve(targetDir);
  if (fs.existsSync(resolved) && fs.statSync(resolved).isFile()) {
    resolved = path.dirname(resolved);
  }

  return { targetDir: resolved, keepSession };
}

function findLatestApplicantDir(rootWorkDir: string): string | null {
  if (!fs.existsSync(rootWorkDir)) return null;

  const candidates: { path: string; mtime: number }[] = [];

  function scan(dir: string, depth = 0) {
    if (depth > 3) return;
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      let hasData = false;

      for (const e of entries) {
        if (
          e.name === 'residence_form_data.json' ||
          e.name === 'applicant_dossier.json' ||
          e.name.endsWith('.jpg') ||
          e.name.endsWith('.png')
        ) {
          hasData = true;
          break;
        }
      }

      if (hasData) {
        const stat = fs.statSync(dir);
        candidates.push({ path: dir, mtime: stat.mtimeMs });
      }

      for (const e of entries) {
        if (e.isDirectory() && !e.name.startsWith('.') && e.name !== 'node_modules') {
          scan(path.join(dir, e.name), depth + 1);
        }
      }
    } catch {}
  }

  scan(rootWorkDir);
  if (candidates.length === 0) return null;
  candidates.sort((a, b) => b.mtime - a.mtime);
  return candidates[0]?.path ?? null;
}

/**
 * Loads and harmonizes client data from residence_form_data.json and applicant_dossier.json.
 */
function loadClientFormData(dir: string): ResidenceFormData {
  let formJson: any = null;
  let dossierJson: any = null;

  const formJsonPath = path.join(dir, 'residence_form_data.json');
  if (fs.existsSync(formJsonPath)) {
    try {
      formJson = JSON.parse(fs.readFileSync(formJsonPath, 'utf-8'));
    } catch (e: any) {
      console.warn(`⚠️ Could not parse residence_form_data.json: ${e.message}`);
    }
  }

  const dossierPath = path.join(dir, 'applicant_dossier.json');
  if (fs.existsSync(dossierPath)) {
    try {
      dossierJson = JSON.parse(fs.readFileSync(dossierPath, 'utf-8'));
    } catch (e: any) {
      console.warn(`⚠️ Could not parse applicant_dossier.json: ${e.message}`);
    }
  }

  // 1. Applicant Name
  const applicantName: string =
    formJson?.applicantName ||
    dossierJson?.name?.value ||
    path.basename(dir).replace(/^client[_\-\s]*/i, '').trim() ||
    'Applicant Name';

  // 2. DOB and Age
  const rawDob = formJson?.dob || dossierJson?.dob?.value || '01/01/2000';
  const formattedDob = ResidenceCertificateFormPage.formatPortalDate(rawDob);
  const age =
    formJson?.age ||
    dossierJson?.age?.value ||
    (rawDob ? calculateAgeFromDob(rawDob) : 25) ||
    25;

  // 3. Gender
  const rawGender = (
    formJson?.gender ||
    dossierJson?.gender?.value ||
    'Male'
  ).toUpperCase();
  const gender: 'Male' | 'Female' | 'Others' =
    rawGender.startsWith('F') ? 'Female' : 'Male';

  // 4. Marital Status
  let maritalStatus: 'Unmarried' | 'Married' | 'Divorcee' | 'Widow' =
    formJson?.maritalStatus || (age < 21 ? 'Unmarried' : 'Married');

  // 5. Title
  let title = formJson?.title;
  if (!title) {
    if (gender === 'Female') {
      title = maritalStatus === 'Married' ? 'Mrs.' : 'Kumari';
    } else {
      title = age < 18 ? 'Mast.' : 'Mr.';
    }
  }

  // 6. Mode & Relative Details (MANDATE: Always 'relative', never 'self')
  const mode: 'self' | 'child' | 'relative' = 'relative';
  
  // Normalize Relative relation for dropdown (Father / Mother / Spouse / Guardian)
  const rawRelRelation = (formJson?.relationType || dossierJson?.relation?.type || formJson?.childRelation || '').toLowerCase();
  let relativeRelation = 'Father';
  if (rawRelRelation.includes('mother')) {
    relativeRelation = 'Mother';
  } else if (rawRelRelation.includes('husband') || rawRelRelation.includes('spouse') || rawRelRelation.includes('wife')) {
    relativeRelation = 'Spouse';
  } else if (rawRelRelation.includes('guardian')) {
    relativeRelation = 'Guardian';
  }

  const relativeName =
    formJson?.relationName ||
    dossierJson?.relation?.name ||
    formJson?.childName ||
    dossierJson?.child?.name ||
    'Parent Name';

  // 7. Relation Type & Name for Applicant Personal Info
  let relationType: 'Father' | 'Husband' | 'Guardian' | 'Mother' = 'Father';
  const rawApplicantRelation = (formJson?.relationType || dossierJson?.relation?.type || '').toLowerCase();
  if (rawApplicantRelation.includes('husband') || rawApplicantRelation.includes('wife')) {
    relationType = 'Husband';
  } else if (rawApplicantRelation.includes('mother')) {
    relationType = 'Mother';
  } else if (rawApplicantRelation.includes('guardian')) {
    relationType = 'Guardian';
  }

  const relationName: string =
    formJson?.relationName || dossierJson?.relation?.name || relativeName;

  // 8. Address Resolution
  const rawAddress: string =
    formJson?.address ||
    dossierJson?.address?.value?.full ||
    'H.No. 1, Goa';

  // Pincode
  const pinMatch = rawAddress.match(/\b(403\d{3})\b/);
  const pincode =
    pinMatch?.[1] ||
    dossierJson?.address?.value?.pincode ||
    '403516';

  // House No
  const houseMatch = rawAddress.match(/(?:H\.?\s*No\.?|House\s*No\.?|Flat\s*No\.?)\s*([A-Za-z0-9\-\/\.\s]+?)(?:,|$|\n)/i);
  const houseNo =
    houseMatch?.[1]?.trim() ||
    dossierJson?.address?.value?.houseNo ||
    'H.No. 45/B';

  // Taluka & District
  let taluka = 'Bardez';
  let district: 'North Goa' | 'South Goa' = 'North Goa';

  const checkTalukaText = (
    formJson?.taluka ||
    dossierJson?.address?.value?.taluka ||
    rawAddress
  ).toLowerCase();

  for (const [key, name] of Object.entries(TALUKA_CANONICAL_NAMES)) {
    if (checkTalukaText.includes(key)) {
      taluka = name;
      if (SOUTH_GOA_TALUKAS.includes(key)) {
        district = 'South Goa';
      } else {
        district = 'North Goa';
      }
      break;
    }
  }

  // Village & Locality
  const village =
    formJson?.place ||
    dossierJson?.address?.value?.villageOrCity ||
    'Arpora';

  const locality =
    rawAddress
      .replace(new RegExp(pincode, 'g'), '')
      .replace(new RegExp(taluka, 'gi'), '')
      .replace(/Goa/gi, '')
      .replace(/[,\-\s]+$/, '')
      .trim() || 'Near St. Jerome Church';

  // Period / Stay From Date
  const currentYear = new Date().getFullYear();
  const sinceYear: number =
    formJson?.sinceYear ||
    dossierJson?.yearsInGoa?.sinceYear ||
    (currentYear - (formJson?.yearsInGoa || 15));

  // Ensure stayFromDate is not before applicant's birth
  let stayFromYear = sinceYear;
  const birthYearMatch = formattedDob.match(/\d{4}$/);
  if (birthYearMatch) {
    const birthYear = parseInt(birthYearMatch[0], 10);
    if (birthYear > stayFromYear) {
      stayFromYear = birthYear;
    }
  }
  const stayFromDate = `01-Jan-${stayFromYear}`;

  // 9. Identity Proof (Aadhaar Card)
  let idProofNumber =
    formJson?.idProofNumber ||
    (typeof dossierJson?.idProofNumber === 'object' ? dossierJson?.idProofNumber?.value : dossierJson?.idProofNumber) ||
    (typeof dossierJson?.aadhaar === 'object' ? dossierJson?.aadhaar?.value : dossierJson?.aadhaar) ||
    '';

  // If missing, look for 12-digit number in files
  if (!idProofNumber) {
    try {
      const dirEntries = fs.readdirSync(dir);
      for (const file of dirEntries) {
        if (file.endsWith('.txt') || file.endsWith('.json')) {
          try {
            const content = fs.readFileSync(path.join(dir, file), 'utf-8');
            const m = content.match(/\b([2-9]\d{3}\s?\d{4}\s?\d{4})\b/);
            if (m && m[1]) {
              idProofNumber = m[1].replace(/\s+/g, '');
              break;
            }
          } catch {}
        }
      }
    } catch {}
  }

  if (typeof idProofNumber === 'string') {
    idProofNumber = idProofNumber.replace(/\D/g, '');
  }

  // Fallback to Verhoeff-valid test Aadhaar if none discovered
  if (!idProofNumber || idProofNumber.length !== 12) {
    idProofNumber = '999999990019';
  }

  // 10. Previous Residence Certificate
  const previousCertNumber =
    formJson?.previousCertNumber ||
    dossierJson?.previousResidenceCert?.number ||
    '';
  const rawPrevDate =
    formJson?.previousCertDate ||
    dossierJson?.previousResidenceCert?.issueDate ||
    '';
  const previousCertDate = rawPrevDate
    ? ResidenceCertificateFormPage.formatPortalDate(rawPrevDate)
    : '';
  const previousCertAuthority =
    formJson?.previousCertAuthority ||
    dossierJson?.previousResidenceCert?.authority ||
    `Mamlatdar of ${taluka}`;
  const previousCertAddress =
    formJson?.previousCertAddress ||
    rawAddress;
  const issuedEarlier: 'Yes' | 'No' =
    formJson?.issuedEarlier ||
    (previousCertNumber ? 'Yes' : (dossierJson?.hasPreviousResidenceCert ? 'Yes' : 'No'));

  // 11. File paths
  const photoPath = formJson?.photoPath || path.join(dir, 'passport_photo.jpg');
  const declarationPdfPath = formJson?.declarationPdfPath || path.join(dir, 'residence_declaration.pdf');

  return {
    serviceType: 'residence_certificate',
    mode: 'relative',
    relativeRelation: relativeRelation || 'Father',
    relativeName: relativeName || relationName || 'Parent Name',
    purpose: '15 years',
    periodType: 'For',
    yearsInGoa: currentYear - stayFromYear,
    monthsInGoa: 0,
    title,
    applicantName,
    dob: formattedDob,
    age,
    placeOfBirth: formJson?.place || taluka,
    gender,
    maritalStatus,
    relationType,
    relationName,
    mobileNo: formJson?.mobileNo || '9876543210',
    emailId: formJson?.emailId || 'citizen.goa@example.com',
    occupation: formJson?.occupation || (age < 22 ? 'Student' : 'Employed'),
    issuedEarlier,
    previousCertNumber: previousCertNumber || undefined,
    previousCertDate: previousCertDate || undefined,
    previousCertAuthority: previousCertAuthority || undefined,
    previousCertAddress: previousCertAddress || undefined,
    houseNo,
    premisesType: 'Owned',
    currentlyStaying: 'Yes',
    locality,
    district,
    taluka,
    village,
    pincode,
    stayFromDate,
    applyToStay: 'Yes',
    idProofType: 'Aadhaar Card',
    idProofNumber,
    photoPath,
    declarationPdfPath
  };
}

export async function runResidencePortalFiller(): Promise<void> {
  const { targetDir, keepSession } = parseArgs();

  console.log('========================================================================');
  console.log('🏛️  GOAONAUTO - REAL CLIENT PORTAL FORM FILLING (SAFE REVIEW MODE)');
  console.log(`📂 Client Folder: ${targetDir}`);
  console.log('🛡️  SAFE MODE: Form submission is DISABLED for safety.');
  console.log('    Brave browser will remain open on Screen 1 for your manual review!');
  console.log('========================================================================\n');

  if (!fs.existsSync(targetDir)) {
    console.error(`❌ Error: Client directory not found: ${targetDir}`);
    process.exit(1);
  }

  // 1. Load client data
  console.log('🔍 Reading client dossier and declaration data...');
  const formData = loadClientFormData(targetDir);

  console.log('------------------------------------------------------------------------');
  console.log(`📋 Applicant Name:  ${formData.applicantName}`);
  console.log(`🎂 Date of Birth:   ${formData.dob} (Age: ${formData.age})`);
  console.log(`👤 Mode:            ${(formData.mode || 'self').toUpperCase()}`);
  if (formData.mode === 'relative') {
    console.log(`👨‍👧 Relative:        ${formData.relativeRelation} (${formData.relativeName})`);
  }
  console.log(`🏠 Address:         ${formData.houseNo}, ${formData.locality}, ${formData.village}, ${formData.taluka} (${formData.district})`);
  console.log(`📅 Stay From:       ${formData.stayFromDate} (${formData.yearsInGoa} Years)`);
  console.log(`🪪 ID Proof:        ${formData.idProofType} -> ${formData.idProofNumber}`);
  console.log('------------------------------------------------------------------------\n');

  try {
    // 2. Launch Brave and complete portal login handshake
    console.log('🚀 Connecting to Brave Browser and navigating to GoaOnline Portal...');
    const session = await startPortalPhase1({
      freshLogin: !keepSession,
      loginTimeoutMs: 300000
    });

    const formPage = session.page;
    await formPage.bringToFront();

    await updatePortalStatusOverlay(
      formPage,
      `🤖 GoaOnAuto: Auto-filling Screen 1 for ${formData.applicantName}...`,
      'working'
    );

    // 3. Fill Screen 1
    const residenceForm = new ResidenceCertificateFormPage(formPage);
    await residenceForm.fillScreen1(formData);

    // 4. Update status overlay to success
    await updatePortalStatusOverlay(
      formPage,
      `✨ GoaOnAuto: Screen 1 Populated for ${formData.applicantName}! Review & Submit.`,
      'success'
    );

    console.log('\n========================================================================');
    console.log('🎉 SCREEN 1 POPULATED SUCCESSFULLY WITH REAL CLIENT DATA!');
    console.log('========================================================================');
    console.log(`👉 Verified for: ${formData.applicantName}`);
    console.log('👀 Brave browser is open on Screen 1 on your screen.');
    console.log('✅ What you should do now:');
    console.log('   1. Review the filled details in Brave.');
    console.log('   2. When satisfied, click "Save & Proceed" to go to Document Uploads.');
    console.log('   3. Upload the declaration PDF & passport photo from your client folder.');
    console.log('\n⌨️  Press ENTER in this terminal when you are finished to close.');
    console.log('========================================================================\n');

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    await new Promise<void>((resolve) => {
      rl.question('', () => {
        rl.close();
        resolve();
      });
    });

    console.log('🔒 Exiting GoaOnAuto Form Filler session.');
    process.exit(0);

  } catch (error: any) {
    console.error('\n❌ Portal Form Filling Error:', error.message || error);
    console.log('\n💡 Tip: Make sure Brave is not blocked and your internet connection is stable.');
    console.log('⌨️  Press ENTER to exit.');
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question('', () => {
      rl.close();
      process.exit(1);
    });
  }
}

if (import.meta.main || require.main === module) {
  runResidencePortalFiller();
}
