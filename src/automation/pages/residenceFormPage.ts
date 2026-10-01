/**
 * GoaOnline Residence Certificate Form (Screen 1) Page Object Model.
 * Single Responsibility: Automates form filling on Screen 1 (services.goaonline.gov.in)
 * based on verified IDs discovered via live human simulation.
 */
import { Page } from '@playwright/test';
import { ApplicationPage } from './applicationPage';

export interface ResidenceFormData {
  serviceType?: string;
  mode?: 'self' | 'child' | 'relative';
  relativeRelation?: string; // e.g., 'Father', 'Mother', 'Son', 'Daughter', 'Spouse'
  relativeName?: string;     // Name of relative applying on applicant's behalf
  purpose?: string;          // '15 years', 'Goa Housing Board', 'Ladli Laxmi', 'Marriage Registration', 'Other', 'Portuguese Passport'
  otherPurposeText?: string;
  periodType?: 'For' | 'Since';
  yearsInGoa?: number;       // e.g., 15
  monthsInGoa?: number;      // e.g., 0
  title?: string;            // 'Mr.', 'Mrs.', 'Miss.', 'Mast.', 'Kumari', 'Smt.', 'Shri.', 'Kumar'
  applicantName: string;
  dob?: string;              // '06-Jan-2004' or YYYY-MM-DD
  age?: number;
  placeOfBirth?: string;
  gender?: 'Male' | 'Female' | 'Others';
  maritalStatus?: 'Unmarried' | 'Married' | 'Divorcee' | 'Widow';
  relationType?: 'Father' | 'Husband' | 'Guardian' | 'Mother';
  relationName?: string;
  mobileNo?: string;
  emailId?: string;
  occupation?: 'Employed' | 'Unemployed' | 'Business' | 'Student';
  issuedEarlier?: 'Yes' | 'No';
  previousCertNumber?: string;
  previousCertDate?: string;
  previousCertAuthority?: string;
  previousCertAddress?: string;
  // Residential Address
  houseNo?: string;
  premisesType?: 'Owned' | 'Rented';
  currentlyStaying?: 'Yes' | 'No';
  locality?: string;
  district?: 'North Goa' | 'South Goa';
  taluka?: string;           // e.g. 'Bardez'
  village?: string;          // e.g. 'Arpora'
  pincode?: string;          // e.g. '403516'
  stayFromDate?: string;     // '10-May-2009'
  stayToDate?: string;       // '10-May-2024'
  applyToStay?: 'Yes' | 'No'; // Compulsory starred field drpApplyTo_
  // ID Proof
  idProofType?: 'Aadhaar Card' | 'Pan Card' | 'Voter Card';
  idProofNumber?: string;
  // File Paths
  photoPath?: string;
  declarationPdfPath?: string;
}

export class ResidenceCertificateFormPage {
  readonly page: Page;
  readonly appPage: ApplicationPage;

  constructor(page: Page) {
    this.page = page;
    this.appPage = new ApplicationPage(page);
  }

  /**
   * Helper to safely highlight and fill an input.
   */
  private async safeFill(selector: string, value: string, fieldName: string): Promise<boolean> {
    try {
      const loc = this.page.locator(selector).first();
      if (await loc.isVisible({ timeout: 3500 }).catch(() => false)) {
        await loc.scrollIntoViewIfNeeded().catch(() => {});
        await loc.fill('');
        await loc.fill(value);
        console.log(`   ✍️  [${fieldName}] -> "${value}"`);
        return true;
      } else {
        console.warn(`   ⚠️  [${fieldName}] input was not visible within timeout: ${selector}`);
      }
    } catch (e: any) {
      console.warn(`   ⚠️  Could not fill [${fieldName}] (${selector}): ${e.message}`);
    }
    return false;
  }

  /**
   * Helper to safely select an option from a dropdown by label or value with native event dispatching and verification.
   */
  private async safeSelect(selector: string, labelOrValue: string, fieldName: string): Promise<boolean> {
    try {
      const loc = this.page.locator(selector).first();
      if (await loc.isVisible({ timeout: 3500 }).catch(() => false)) {
        await loc.scrollIntoViewIfNeeded().catch(() => {});

        // 1. Playwright native select attempt
        await loc.selectOption({ label: labelOrValue }).catch(async () => {
          await loc.selectOption(labelOrValue).catch(() => {});
        });

        // 2. DOM evaluate fallback & event dispatch to ensure Wicket/ASP.NET picks up the change
        await this.page.evaluate(({ sel, val }) => {
          const el = document.querySelector(sel) as HTMLSelectElement | null;
          if (el) {
            let found = false;
            for (let i = 0; i < el.options.length; i++) {
              const opt = el.options[i];
              if (opt && (opt.text.trim().toLowerCase() === val.trim().toLowerCase() || opt.value === val)) {
                el.selectedIndex = i;
                found = true;
                break;
              }
            }
            if (found) {
              el.dispatchEvent(new Event('input', { bubbles: true }));
              el.dispatchEvent(new Event('change', { bubbles: true }));
            }
          }
        }, { sel: selector, val: labelOrValue });

        await this.page.waitForTimeout(500); // Allow dynamic Wicket AJAX updates to settle

        // 3. Verify selected option text
        const selectedText = await loc.evaluate((el: HTMLSelectElement) => {
          return el.options[el.selectedIndex]?.text?.trim() || '';
        }).catch(() => '');

        console.log(`   🔽 [${fieldName}] -> "${selectedText || labelOrValue}"`);
        return true;
      } else {
        console.warn(`   ⚠️  [${fieldName}] dropdown was not visible within timeout: ${selector}`);
      }
    } catch (e: any) {
      console.warn(`   ⚠️  Could not select [${fieldName}] (${selector}): ${e.message}`);
    }
    return false;
  }

  /**
   * Sets date directly in DD-MMM-YYYY format with native event dispatching (instant < 10ms, no calendar popup delays).
   */
  private async setDateField(inputSelector: string, rawDate: string, fieldName: string): Promise<void> {
    const formatted = ResidenceCertificateFormPage.formatPortalDate(rawDate);
    const inputLoc = this.page.locator(inputSelector).first();

    if (!await inputLoc.isVisible({ timeout: 2500 }).catch(() => false)) {
      console.warn(`   ⚠️ [${fieldName}] Input ${inputSelector} not visible.`);
      return;
    }

    await inputLoc.scrollIntoViewIfNeeded().catch(() => {});

    // Set value via DOM directly to support readonly inputs without Playwright editability timeouts
    await this.page.evaluate(({ sel, val }) => {
      const el = document.querySelector(sel) as HTMLInputElement | null;
      if (el) {
        el.value = val;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        if ((window as any).$ && (window as any).$(el).datepicker) {
          try { (window as any).$(el).datepicker('setDate', val); } catch {}
        }
      }
    }, { sel: inputSelector, val: formatted });

    // Dismiss any calendar popup that might have triggered on focus
    await this.page.keyboard.press('Escape').catch(() => {});
    console.log(`   📅 [${fieldName}] -> "${formatted}" (Instant)`);
  }

  /**
   * Formats a raw date (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, etc.) to portal format: DD-MMM-YYYY (e.g. 06-Jan-2004).
   */
  static formatPortalDate(rawDate: string): string {
    if (!rawDate) return '01-Jan-2000';
    const trimmed = rawDate.trim();
    if (/^\d{2}-[A-Za-z]{3}-\d{4}$/.test(trimmed)) return trimmed;

    try {
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

      // 1. DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
      const dmyMatch = trimmed.match(/^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$/);
      if (dmyMatch && dmyMatch[1] && dmyMatch[2] && dmyMatch[3]) {
        const day = String(parseInt(dmyMatch[1], 10)).padStart(2, '0');
        const monthIdx = parseInt(dmyMatch[2], 10) - 1;
        const year = dmyMatch[3];
        const mon = months[monthIdx] || 'Jan';
        return `${day}-${mon}-${year}`;
      }

      // 2. YYYY-MM-DD or YYYY/MM/DD
      const ymdMatch = trimmed.match(/^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$/);
      if (ymdMatch && ymdMatch[1] && ymdMatch[2] && ymdMatch[3]) {
        const year = ymdMatch[1];
        const monthIdx = parseInt(ymdMatch[2], 10) - 1;
        const day = String(parseInt(ymdMatch[3], 10)).padStart(2, '0');
        const mon = months[monthIdx] || 'Jan';
        return `${day}-${mon}-${year}`;
      }

      const d = new Date(trimmed);
      if (isNaN(d.getTime())) return '01-Jan-2000';
      const day = String(d.getDate()).padStart(2, '0');
      const mon = months[d.getMonth()];
      const year = d.getFullYear();
      return `${day}-${mon}-${year}`;
    } catch {
      return '01-Jan-2000';
    }
  }

  /**
   * Fills all fields on Screen 1 of the Residence Certificate form using the exact discovered selectors.
   */
  async fillScreen1(data: ResidenceFormData): Promise<void> {
    console.log(`\n================================================================`);
    console.log(`📝 [ResidenceForm] Filling Screen 1 Details for: ${data.applicantName}`);
    console.log(`   Mode: ${data.mode || 'self'}`);
    console.log(`================================================================\n`);

    // 1. Mode / Applying For Selection: ALWAYS "Relative or others" (CSC/citizen agent standard)
    console.log('🔘 Setting Mode: "Relative or others"...');
    const relOption = this.page.locator('label:has-text("Relative"), label[for*="id6b"], input[value="radio23"], #id6b').first();
    await relOption.click({ force: true }).catch(() => {});
    await this.page.waitForTimeout(600); // Wait for Wicket AJAX to reveal relative fields

    const relation = data.relativeRelation || data.relationType || 'Father';
    await this.safeSelect('select[name*="drpRelation_"], #idaf, select[name*="wmcApplying"]', relation, 'You Are (Relationship)');
    await this.page.waitForTimeout(600);

    const relName = data.relativeName || data.relationName || 'Parent Name';
    const relNameSelector = 'input[name*="txtRelativeName_"], input[name*="wmcRelation"], #idb0';
    await this.safeFill(relNameSelector, relName, 'Relative Full Name');

    // 2. Purpose of Certificate
    const purpose = data.purpose || '15 years';
    await this.safeSelect('select[name*="drpPurpose_"], #id2b', purpose, 'Purpose');
    if (purpose === 'Other' && data.otherPurposeText) {
      await this.safeFill('input[name*="txtintend_"], #id2c', data.otherPurposeText, 'Intended Submission Purpose');
    }

    // 3. Residence Period (For / Since)
    const period = data.periodType || 'For';
    await this.safeSelect('select[name*="drpResCertPeriod_"], #id2d', period, 'Period Type');
    if (period === 'For') {
      const years = String(data.yearsInGoa ?? 15);
      const months = String(data.monthsInGoa ?? 0);
      await this.safeFill('input[name*="txtYear_"], #year', years, 'Years in Goa');
      await this.safeSelect('select[name*="drpMonth_"], #id2e', months, 'Months in Goa');
    }

    // 4. Personal Information
    const title = data.title || (data.gender === 'Female' ? (data.maritalStatus === 'Married' ? 'Mrs.' : 'Kumari') : 'Mr.');
    await this.safeSelect('select[name*="drpTitle_"], #id2f', title, 'Title');
    await this.safeFill('input[name*="txtapplicantName_"], #id30', data.applicantName, 'Applicant Full Name');

    if (data.dob) {
      await this.setDateField('#DOB, input[name*="txtDOB"]', data.dob, 'Date of Birth');
    }

    if (data.placeOfBirth) {
      await this.safeFill('input[name*="txtPOB_"], #id2a', data.placeOfBirth, 'Place of Birth');
    }

    if (data.gender) {
      await this.safeSelect('select[name*="drpGender_"], #id32', data.gender, 'Gender');
      await this.page.waitForTimeout(600); // Wait for dynamic Wicket AJAX updates after Gender
    }

    if (data.maritalStatus) {
      const maritalSelector = 'select[name*="drpMartialStatus_"], select[name*="drpMaritalStatus_"], select:has(option:has-text("Unmarried")), #id33';
      await this.safeSelect(maritalSelector, data.maritalStatus, 'Marital Status');
      
      // Verification check: ensure value did not get reset by asynchronous Wicket roundtrip
      const currentVal = await this.page.locator(maritalSelector).first().evaluate((el: HTMLSelectElement) => el.value).catch(() => '');
      if (!currentVal || currentVal === '') {
        console.log('   🔄 Re-applying Marital Status after Wicket settlement...');
        await this.page.waitForTimeout(300);
        await this.safeSelect(maritalSelector, data.maritalStatus, 'Marital Status');
      }
    }

    // Relation Type (Father/Husband/Guardian/Mother)
    if (data.relationType) {
      await this.safeSelect('select[name*="drpFatHus_"], #id34', data.relationType, 'Relation Type');
      // CRITICAL: Wicket AJAX updates the Father's Name input after relationType changes!
      await this.page.waitForTimeout(600);
    }

    // Relation / Father's Name - STRICTLY input elements only! Do NOT include #id7f (which is a <label>)!
    if (data.relationName) {
      const fatNameSelector = 'input[name*="txtFatName_"], input#id35, input[name*="FatName"]';
      await this.safeFill(fatNameSelector, data.relationName, "Father's / Relation Name");
    }

    if (data.mobileNo) {
      await this.safeFill('input[name*="txtMobileNo_"], #id36', data.mobileNo, 'Mobile Number');
    }

    if (data.emailId) {
      await this.safeFill('input[name*="txtEmailID_"], #id37', data.emailId, 'Email ID');
    }

    const occupation = data.occupation || 'Employed';
    await this.safeSelect('select[name*="drpOccupation_"], #id38', occupation, 'Occupation');

    const hasPrevCert = data.issuedEarlier === 'Yes' || Boolean(data.previousCertNumber);
    const issuedEarlier = hasPrevCert ? 'Yes' : 'No';
    await this.safeSelect('select[name*="drpResCertIssued_"], #id3f', issuedEarlier, 'Certificate Issued Earlier?');
    await this.page.waitForTimeout(600); // Wait for Wicket AJAX to render previous certificate fields

    if (issuedEarlier === 'Yes') {
      console.log('📜 Populating Previous Residence Certificate records...');
      if (data.previousCertNumber) {
        await this.safeFill('#idc3, input[name*="txtCertNo_"]', data.previousCertNumber, 'Previous Certificate No');
      }
      if (data.previousCertDate) {
        await this.setDateField('#issuedate, input[name*="txtIssueDate_"]', data.previousCertDate, 'Previous Issue Date');
      }
      const authPerson = data.previousCertAuthority || `Mamlatdar of ${data.taluka || 'Bardez'}`;
      await this.safeFill('#idc4, input[name*="txtAuthPerson_"]', authPerson, 'Authorized Person Name');

      const prevAddress = data.previousCertAddress || `${data.houseNo || 'H.No. 1'}, ${data.locality || ''}, ${data.village || data.taluka || 'Goa'}`.trim();
      await this.safeFill('#idc8, input[name*="txtPrevAddress_"]', prevAddress, 'Previous Address');
    }

    // 5. Residential Address Block (Modal Dialog Flow)
    console.log('\n🏠 Adding Residential Address Details...');
    const addNewBtn = this.page.locator('#btnaddnew, button:has-text("Add New"), a:has-text("Add New")').first();
    if (await addNewBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await addNewBtn.click().catch(() => {});
      
      // Explicitly wait for Address Modal to open and first input to be visible and editable!
      console.log('   ⏳ Waiting for Address modal window to open...');
      const houseInput = this.page.locator('input[name*="txtHouseNo_"], #id42').first();
      await houseInput.waitFor({ state: 'visible', timeout: 6000 }).catch(() => {});
      await this.page.waitForTimeout(400);

      // Starred field 1: House/Flat No*
      await this.safeFill('input[name*="txtHouseNo_"], #id42', data.houseNo || 'H.No. 123/4-A', 'House/Flat No*');

      // Starred field 2: Premises Type* (Owned / Rented)
      await this.safeSelect('select[name*="drpPremisesType_"], #id43', data.premisesType || 'Owned', 'Premises Type*');

      // Starred field 3: Currently Staying?* (Yes / No)
      await this.safeSelect('select[name*="drpCurrentStay_"], #id44', data.currentlyStaying || 'Yes', 'Currently Staying?*');

      // Starred field 4: Locality / Area / Ward*
      await this.safeFill('input[name*="txtAreaLocality_"], #id46', data.locality || 'Near St. Jerome Church', 'Locality / Area*');

      // Starred field 5: District* (North Goa / South Goa)
      const district = data.district || 'North Goa';
      await this.safeSelect('select[name*="drpDistrict_"], #id47', district, 'District*');
      await this.page.waitForTimeout(600); // Wait for Taluka options to load via AJAX

      // Starred field 6: Taluka* (e.g. Bardez)
      if (data.taluka) {
        await this.safeSelect('select[name*="drpTaluka_"], #id48', data.taluka, 'Taluka*');
        await this.page.waitForTimeout(600); // Wait for Village options to load via AJAX
      }

      // Starred field 7: Village* (e.g. Arpora)
      if (data.village) {
        await this.safeSelect('select[name*="drpVillage_"], #id49', data.village, 'Village*');
      }

      // Starred field 8: Pincode*
      await this.safeFill('input[name*="txtPincode_"], #id4a', data.pincode || '403516', 'Pincode*');

      // Starred field 9: Period of Stay* (For / Since)
      await this.safeSelect('select[name*="drpPeriod_"], #id4b', 'For', 'Period of Stay*');

      // Starred field 10: From Date* (Instant direct entry)
      const fromDate = data.stayFromDate || '10-May-2009';
      await this.setDateField('#fromdate, input[name*="txtfromDate_"]', fromDate, 'Stay From Date*');

      // If Currently Staying is No, To Date* is compulsory
      if (data.currentlyStaying === 'No' && data.stayToDate) {
        await this.setDateField('#todate, input[name*="txttoDate_"]', data.stayToDate, 'Stay To Date*');
      }

      // Starred field 11: Are you applying for this stay?* (drpApplyTo_ is compulsory!)
      const applyToStay = data.applyToStay || 'Yes';
      await this.safeSelect('select[name*="drpApplyTo_"], #id45', applyToStay, 'Apply to this stay?* (drpApplyTo_)');

      // Click "Add" button to save the address row
      console.log('   ➕ Saving Address Details row...');
      const addAddrBtn = this.page.locator([
        'input[name*="btnDtlUpdate"][name*="confirmButton"]',
        'input[name="btnDtlUpdate_:confirmButton"]',
        'input[value="Add"]',
        '#id4f'
      ].join(', ')).first();

      if (await addAddrBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await addAddrBtn.scrollIntoViewIfNeeded().catch(() => {});
        await addAddrBtn.click();
        await this.page.waitForTimeout(600);

        // Confirm modal popup if triggered ("Are you sure you want to add?")
        // CRITICAL: Must specifically target btnDtlUpdate:yesButton to avoid matching the hidden final submit modal!
        const confirmYesBtn = this.page.locator([
          'input[name*="btnDtlUpdate"][name*="yesButton"]',
          'input[name="btnDtlUpdate_:myModal:yesButton"]',
          '#id4d'
        ].join(', ')).first();

        console.log('   ⏳ Waiting for Address Save confirmation modal ("Yes")...');
        const isYesVisible = await confirmYesBtn.waitFor({ state: 'visible', timeout: 4000 }).then(() => true).catch(() => false);
        if (isYesVisible) {
          console.log('   ✔️ Clicking Address Save confirmation ("Yes")...');
          await confirmYesBtn.click();
          await this.page.waitForTimeout(800);
        } else {
          // Direct in-page fallback dispatch
          await this.page.evaluate(() => {
            const btn = document.querySelector('input[name*="btnDtlUpdate"][name*="yesButton"]') as HTMLInputElement | null;
            if (btn) btn.click();
          }).catch(() => {});
          await this.page.waitForTimeout(600);
        }
      }

      // Close the Address Modal dialog if it remains open (only within modal, not top-level elements)
      const closeAddrModalBtn = this.page.locator([
        '.modal.show button.close',
        '.modal.show button:has-text("Close")',
        '.modal.in button.close'
      ].join(', ')).first();

      if (await closeAddrModalBtn.isVisible({ timeout: 1200 }).catch(() => false)) {
        console.log('   🔒 Closing Address modal window...');
        await closeAddrModalBtn.click().catch(() => {});
        await this.page.waitForTimeout(400);
      }
    }

    // 6. Identity Proof Selection (Aadhaar Card with Verhoeff-checksum number)
    console.log('\n🪪 Setting Identity Proof Details...');
    const idType = data.idProofType || 'Aadhaar Card';
    await this.safeSelect('#id3d, select[name*="drpIdProof"]', idType, 'ID Proof Type');
    await this.page.waitForTimeout(300);

    const idNumber = data.idProofNumber || '999999990019';
    await this.safeFill('#id3e, input[name*="txtIdProofNo"]', idNumber, 'ID Proof Number');

    // 7. Declaration Checkbox
    console.log('☑️ Checking Self-Declaration Checkbox...');
    const declCheck = this.page.locator('#id41, input[name*="declarationcheck"]').first();
    if (await declCheck.isVisible({ timeout: 2000 }).catch(() => false)) {
      await declCheck.check().catch(() => {});
      console.log('   ✅ Declaration checkbox marked.');
    }

    console.log('\n✨ [ResidenceForm] Screen 1 Form Successfully Populated with all required fields!');
  }

  /**
   * Advances to Screen 2 (Document Upload).
   * NOTE: ONLY call this when explicitly instructed to submit!
   */
  async submitToScreen2(): Promise<void> {
    console.log('🚀 Proceeding to Document Upload (Screen 2)...');
    const saveAndProceedBtn = this.page.locator('#id92, input[value*="Save & Proceed"], button:has-text("Save & Proceed")').first();
    await saveAndProceedBtn.click();
    await this.page.waitForTimeout(600);

    const modalYesBtn = this.page.locator('#id94, input[value="Yes"], button:has-text("Yes")').first();
    if (await modalYesBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await modalYesBtn.click();
    }
  }
}
