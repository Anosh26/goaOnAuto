import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import { createWorker, PSM } from 'tesseract.js';
const email = 'citizen@example.com'
const password ='dummy_password'
var captcha ='123456'

async function solveCaptcha(imageBuffer: Buffer): Promise<string> {
  const worker = await createWorker();

  await worker.setParameters({
    tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    tessedit_pageseg_mode: PSM.SINGLE_LINE,
  });

  const { data: { text } } = await worker.recognize(imageBuffer);
  await worker.terminate();
  return text.replace(/\s/g, '');
}

test('Go to Login Page', async ({ page }) => {
  await page.goto('https://goaonline.gov.in/Public/Login');

  // Expect a title "to contain" a substring.
  await expect(page).toHaveTitle(/Goa Online/);
});

test('Login with valid credentials', async ({ page }) => {
  await page.goto('https://goaonline.gov.in/Public/Login');
  await page.getByPlaceholder('Enter Username/Email').fill(email);
  await page.getByPlaceholder('Enter Password').fill(password);
 
  const captchaLocator = page.locator('img#Main_imgCap');
  await expect(captchaLocator).toBeVisible();
  const captchaBuffer = await captchaLocator.screenshot();
  fs.writeFileSync('captcha.png', captchaBuffer);

  const captcha_text = await solveCaptcha(captchaBuffer);
  console.log('Captcha Text:', captcha_text);
  await page.getByPlaceholder('Enter the code shown above').fill(captcha_text);
  await page.getByRole('button', { name: 'Login' }).click();

});

test('Process applicant photo automatically for upload (<50 KB)', async () => {
  const { processPhotoForUpload } = await import('../src/image/photoProcessor');
  const samplePhoto = 'captcha.png';
  if (fs.existsSync(samplePhoto)) {
    const processedPath = await processPhotoForUpload(samplePhoto, { maxKB: 50, useAI: true });
    expect(fs.existsSync(processedPath)).toBe(true);
    const stats = fs.statSync(processedPath);
    expect(stats.size).toBeLessThanOrEqual(50 * 1024);
  }
});
