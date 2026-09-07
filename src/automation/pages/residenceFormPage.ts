/**
 * GoaOnline Residence Certificate Form Page Object Model.
 * Single Responsibility: Loads verified client data from the client directory and fills the portal form.
 */
import * as path from 'path';
import * as fs from 'fs';
import { Page, Locator, expect } from '@playwright/test';
import { ApplicationPage } from './applicationPage';

export interface ResidenceFormData {
  serviceType: string;
  mode: 'self' | 'child';
  applicantName: string;
  age: number;
  relationType: string;
  relationName: string;
  childName?: string;
  childRelation?: string;
  sinceYear: number;
  yearsInGoa: number;
  address: string;
  taluka: string;
  place: string;
  declarationDate: string;
  photoPath: string;
  signaturePath?: string;
  declarationTexPath?: string;
  declarationPdfPath?: string;
  updatedAt?: string;
}

/**
 * Loads the verified residence form data saved by the Raylib GUI from the client directory.
 */
export function loadClientFormData(clientDir: string): ResidenceFormData {
  const formJsonPath = path.join(clientDir, 'residence_form_data.json');
  if (fs.existsSync(formJsonPath)) {
    const raw = fs.readFileSync(formJsonPath, 'utf-8');
    return JSON.parse(raw);
  }

  // Fallback to applicant_dossier.json if residence_form_data.json is not yet generated
  const dossierPath = path.join(clientDir, 'applicant_dossier.json');
  if (fs.existsSync(dossierPath)) {
    const dossier = JSON.parse(fs.readFileSync(dossierPath, 'utf-8'));
    const currentYear = new Date().getFullYear();
    const yearsInGoa = dossier.yearsInGoa?.value || 15;

    return {
      serviceType: 'residence_certificate',
      mode: dossier.child?.name ? 'child' : 'self',
      applicantName: dossier.name?.value || '',
      age: dossier.age?.value || 25,
      relationType: dossier.relation?.type || 'Daughter of',
      relationName: dossier.relation?.name || '',
      childName: dossier.child?.name || '',
      childRelation: dossier.child?.relation || 'Daughter',
      sinceYear: currentYear - yearsInGoa,
      yearsInGoa,
      address: dossier.address?.value?.full || '',
      taluka: dossier.address?.value?.taluka || 'Bardez',
      place: 'Mapusa',
      declarationDate: new Date().toLocaleDateString('en-GB'),
      photoPath: dossier.photoPath || '',
      signaturePath: dossier.signaturePath || '',
      declarationPdfPath: dossier.declarationPdf || ''
    };
  }

  throw new Error(`No client form data found in directory: ${clientDir}`);
}

export class ResidenceCertificateFormPage {
  readonly page: Page;
  readonly appPage: ApplicationPage;

  // Form Field Locators (Standard GoaOnline Residence Certificate Form)
  readonly applicantNameInput: Locator;
  readonly ageInput: Locator;
  readonly relationTypeSelect: Locator;
  readonly relationNameInput: Locator;
  readonly yearsInGoaInput: Locator;
  readonly addressInput: Locator;
  readonly talukaSelect: Locator;
  readonly declarationFileInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.appPage = new ApplicationPage(page);

    this.applicantNameInput = page.locator('input#txtApplicantName, input[name*="ApplicantName"], input#Main_txtName');
    this.ageInput = page.locator('input#txtAge, input[name*="Age"], input#Main_txtAge');
    this.relationTypeSelect = page.locator('select#ddlRelation, select[name*="Relation"], select#Main_ddlRelation');
    this.relationNameInput = page.locator('input#txtRelationName, input[name*="RelationName"], input#Main_txtFatherName');
    this.yearsInGoaInput = page.locator('input#txtYearsInGoa, input[name*="YearsInGoa"], input#Main_txtYears');
    this.addressInput = page.locator('textarea#txtAddress, textarea[name*="Address"], textarea#Main_txtAddress');
    this.talukaSelect = page.locator('select#ddlTaluka, select[name*="Taluka"], select#Main_ddlTaluka');
    this.declarationFileInput = page.locator('input[type="file"]#fileDeclaration, input[type="file"][name*="Declaration"], input[type="file"].declaration-upload');
    this.submitButton = page.locator('#btnSubmit, input[type="submit"], button[type="submit"]');
  }

  /**
   * Automatically fills in applicant information from client form data.
   */
  async fillFromClientData(data: ResidenceFormData): Promise<void> {
    console.log(`[ResidenceForm] Filling portal form for: ${data.applicantName} (Mode: ${data.mode})`);

    if (await this.applicantNameInput.isVisible()) {
      await this.applicantNameInput.fill(data.applicantName);
    }
    if (await this.ageInput.isVisible()) {
      await this.ageInput.fill(String(data.age));
    }
    if (await this.relationNameInput.isVisible() && data.relationName) {
      await this.relationNameInput.fill(data.relationName);
    }
    if (await this.yearsInGoaInput.isVisible()) {
      await this.yearsInGoaInput.fill(String(data.yearsInGoa));
    }
    if (await this.addressInput.isVisible()) {
      await this.addressInput.fill(data.address);
    }

    // Upload generated residence declaration PDF if available
    if (data.declarationPdfPath && fs.existsSync(data.declarationPdfPath)) {
      console.log(`[ResidenceForm] Uploading declaration PDF: ${data.declarationPdfPath}`);
      if (await this.declarationFileInput.isVisible()) {
        await this.declarationFileInput.setInputFiles(data.declarationPdfPath);
      }
    }

    // Upload processed photo if available
    if (data.photoPath && fs.existsSync(data.photoPath)) {
      await this.appPage.uploadApplicantPhoto(data.photoPath);
    }
  }
}
