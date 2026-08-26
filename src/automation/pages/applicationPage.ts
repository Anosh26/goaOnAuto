/**
 * Portal Service Application Page Object Model.
 * Single Responsibility: Automates photo/document uploads and form submission on GoaOnline service forms.
 */
import { Page, Locator, expect } from '@playwright/test';
import { processPhotoForUpload } from '../../image/photoProcessor';

export class ApplicationPage {
  readonly page: Page;
  readonly photoFileInput: Locator;
  readonly docFileInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.photoFileInput = page.locator('input[type="file"]#Main_filePhoto, input[type="file"].photo-upload, input[type="file"]');
    this.docFileInput = page.locator('input[type="file"]#Main_fileDoc, input[type="file"].doc-upload');
    this.submitButton = page.locator('#Main_btnSubmit, button[type="submit"]');
  }

  /**
   * Automatically processes an applicant photo (AI background removal + JPEG compression < maxKB)
   * and uploads it to the portal form.
   */
  async uploadApplicantPhoto(rawPhotoPath: string, maxKB: number = 50): Promise<string> {
    console.log(`[ApplicationPage] Auto-processing applicant photo: ${rawPhotoPath}`);
    const processedPath = await processPhotoForUpload(rawPhotoPath, { maxKB, useAI: true });

    await expect(this.photoFileInput.first()).toBeVisible({ timeout: 10000 });
    await this.photoFileInput.first().setInputFiles(processedPath);
    console.log(`[ApplicationPage] Successfully set input files -> ${processedPath}`);

    return processedPath;
  }

  /**
   * Uploads supporting document image after compressing to portal limits.
   */
  async uploadDocument(rawDocPath: string, targetLocator?: Locator, maxKB: number = 200): Promise<string> {
    console.log(`[ApplicationPage] Processing document image: ${rawDocPath}`);
    const processedPath = await processPhotoForUpload(rawDocPath, { maxKB, useAI: false });

    const targetInput = targetLocator ?? this.docFileInput.first();
    await targetInput.setInputFiles(processedPath);
    console.log(`[ApplicationPage] Successfully uploaded document -> ${processedPath}`);

    return processedPath;
  }
}
