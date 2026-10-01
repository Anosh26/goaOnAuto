/**
 * Phase 2 Automated Form Filling Test Runner (Dry-Run / Safe Mode).
 * Fills Screen 1 in Relative / Child mode using Aadhaar and calendar datepicker UI,
 * but DOES NOT submit the form to protect the user's account.
 */
import * as readline from 'readline';
import { startPortalPhase1, updatePortalStatusOverlay } from '../src/automation/services/portalSessionManager';
import { ResidenceCertificateFormPage, ResidenceFormData } from '../src/automation/pages/residenceFormPage';

const DUMMY_TEST_DATA: ResidenceFormData = {
  serviceType: 'residence_certificate',
  // 1. Relative / Child Mode (Father applying on behalf of Child/Applicant)
  mode: 'relative',
  relativeRelation: 'Father',
  relativeName: 'Suresh Parab',

  // 2. Purpose & Period
  purpose: '15 years',
  periodType: 'For',
  yearsInGoa: 15,
  monthsInGoa: 0,

  // 3. Applicant Personal Information
  title: 'Kumari',
  applicantName: 'Neha Suresh Parab',
  dob: '10-May-2004',
  placeOfBirth: 'Mapusa',
  gender: 'Female',
  maritalStatus: 'Unmarried',
  relationType: 'Father',
  relationName: 'Suresh Parab',
  mobileNo: '9876543210',
  emailId: 'suresh.parab@example.com',
  occupation: 'Student',
  issuedEarlier: 'No',

  // 4. Residential Address Details (Compulsory Starred Fields)
  houseNo: 'H.No. 45/B',
  premisesType: 'Owned',
  currentlyStaying: 'Yes',
  locality: 'Near St. Jerome Church',
  district: 'North Goa',
  taluka: 'Bardez',
  village: 'Arpora',
  pincode: '403516',
  stayFromDate: '10-May-2009', // Picked using jQuery UI Datepicker calendar
  applyToStay: 'Yes',          // Compulsory drpApplyTo_ field

  // 5. ID Proof: Aadhaar Card with mathematically valid Verhoeff-checksum test number
  idProofType: 'Aadhaar Card',
  idProofNumber: '999999990019'
};

async function runPhase2Test() {
  console.log('========================================================================');
  console.log('🏛️  GOAONAUTO - RESIDENCE AUTOMATION: PHASE 2 (DRY-RUN)');
  console.log('🎯 Scope: Login -> REV05 -> Proceed to Apply -> Screen 1 Form Filling');
  console.log('👨‍👧 Mode:  Relative / Child (Father applying for Applicant)');
  console.log('🪪 ID:    Aadhaar Card (Verhoeff-validated test number: 999999990019)');
  console.log('📅 Date:  Datepicker Calendar UI Interaction');
  console.log('🛡️  SAFE:  Form submission is DISABLED to protect your citizen account');
  console.log('========================================================================\n');

  try {
    const keepSession = process.argv.includes('--keep-session') || true;

    // Step 1: Connect to Brave and navigate to Screen 1
    console.log('🚀 Connecting to Brave and navigating to Screen 1...');
    const session = await startPortalPhase1({
      freshLogin: !keepSession,
      loginTimeoutMs: 300000
    });

    const formPage = session.page;
    await formPage.bringToFront();

    await updatePortalStatusOverlay(formPage, '🤖 GoaOnAuto: Auto-filling Screen 1 (Relative Mode)...', 'working');

    // Step 2: Initialize Page Object Model and fill Screen 1
    const residenceForm = new ResidenceCertificateFormPage(formPage);
    await residenceForm.fillScreen1(DUMMY_TEST_DATA);

    // Step 3: Update overlay to success
    await updatePortalStatusOverlay(formPage, '✨ GoaOnAuto: Screen 1 Populated! (Dry-Run: No Submission)', 'success');

    console.log('\n========================================================================');
    console.log('🎉 PHASE 2 FORM FILLING SUCCESSFUL!');
    console.log('🛑 FORM SUBMISSION WAS BYPASSED to protect your account from bot activity.');
    console.log('👀 Brave browser is open on Screen 1 for your review.');
    console.log('👉 Verify:');
    console.log('   - Mode: "Relative or others" selected with Relation ("Father") & Relative Name');
    console.log("   - Father's Name properly populated under Relation Details");
    console.log('   - Address row added with From Date via calendar UI & modal cleanly closed');
    console.log('   - Aadhaar Card populated with 999999990019 (zero checksum alerts)');
    console.log('   - Declaration checkbox marked');
    console.log('⌨️  Press ENTER in this terminal when you are ready to exit.');
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

    console.log('🔒 Closing browser session...');
    await session.context.close().catch(() => {});
    console.log('✅ Phase 2 dry-run test completed cleanly.');
    process.exit(0);

  } catch (error: any) {
    console.error('\n❌ Phase 2 Test Error:', error.message || error);
    process.exit(1);
  }
}

runPhase2Test();
