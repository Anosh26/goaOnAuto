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
// test('get started link', async ({ page }) => {
//   await page.goto('https://playwright.dev/');

//   // Click the get started link.
//   await page.getByRole('link', { name: 'Get started' }).click();

//   // Expects page to have a heading with the name of Installation.
//   await expect(page.getByRole('heading', { name: 'Installation' })).toBeVisible();
// });
