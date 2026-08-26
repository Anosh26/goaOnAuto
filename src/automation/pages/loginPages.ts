/**
 * Portal Login Page Object Model.
 * Single Responsibility: Interacts with the GoaOnline citizen portal login and OTP form.
 */
import { Page, Locator, expect } from '@playwright/test';
import { solveCaptcha } from '../solver/captchaSolver';

export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly captchaImg: Locator;
  readonly captchaInput: Locator;
  readonly loginButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.getByPlaceholder('Enter Username/Email');
    this.passwordInput = page.getByPlaceholder('Enter Password');
    this.captchaImg = page.locator('img#Main_imgCap');
    this.captchaInput = page.getByPlaceholder('Enter the code shown above');
    this.loginButton = page.locator('#Main_btniLogin');
  }

  async navigate() {
    await this.page.goto('https://goaonline.gov.in/Public/Login');
  }

  async handleCaptcha() {
    await expect(this.captchaImg).toBeVisible();
    const captchaBuffer = await this.captchaImg.screenshot();
    const text = await solveCaptcha(captchaBuffer);
    await this.captchaInput.fill(text);
    return text;
  }

  async login(user: string, pass: string) {
    await this.usernameInput.fill(user);
    await this.passwordInput.fill(pass);
    await this.handleCaptcha();
    await this.loginButton.click();
  }
}
