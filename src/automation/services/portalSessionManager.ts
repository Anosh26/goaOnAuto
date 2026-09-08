/**
 * GoaOnline Portal Session & Browser Lifecycle Manager.
 * Single Responsibility: Launches Brave browser with a persistent automation profile,
 * supervises the human manual login handshake, and navigates to the Residence Certificate service.
 */
import * as path from 'path';
import * as fs from 'fs';
import { chromium, BrowserContext, Page } from '@playwright/test';
import { config } from '../../config';

export interface PortalSessionConfig {
  braveExecutablePath?: string;
  profileDir?: string;
  headless?: boolean;
  loginTimeoutMs?: number;
}

export interface PortalSession {
  context: BrowserContext;
  page: Page;
  currentUrl: string;
}

const GOA_ONLINE_LOGIN_URL = 'https://goaonline.gov.in/Public/Login';
const RESIDENCE_SERVICE_URL = 'https://goaonline.gov.in/Appln/UIL/deptServices?__DocId=REV&__ServiceId=REV05';

/**
 * Resolves the path to the Brave Browser executable on Windows.
 */
export function resolveBravePath(): string {
  if (process.env.BRAVE_PATH && fs.existsSync(process.env.BRAVE_PATH)) {
    return process.env.BRAVE_PATH;
  }

  const standardPaths = [
    'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
    'C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
    path.join(process.env.LOCALAPPDATA || '', 'BraveSoftware', 'Brave-Browser', 'Application', 'brave.exe')
  ];

  for (const p of standardPaths) {
    if (fs.existsSync(p)) return p;
  }

  throw new Error(
    'Brave Browser executable not found! Checked standard locations in Program Files and LocalAppData.\n' +
    'Please ensure Brave is installed or set the BRAVE_PATH environment variable.'
  );
}

/**
 * Resolves the dedicated persistent browser profile directory.
 */
export function resolveProfileDir(customProfileDir?: string): string {
  const profileDir = customProfileDir || path.join(config.projectRoot, '.brave_automation_profile');
  if (!fs.existsSync(profileDir)) {
    fs.mkdirSync(profileDir, { recursive: true });
  }
  return profileDir;
}

/**
 * Launches Brave with a persistent context to retain session and prevent profile lock conflicts.
 */
export async function launchBravePortalContext(sessionConfig: PortalSessionConfig = {}): Promise<{ context: BrowserContext; page: Page }> {
  const bravePath = sessionConfig.braveExecutablePath || resolveBravePath();
  const profileDir = resolveProfileDir(sessionConfig.profileDir);

  console.log(`🚀 [PortalSession] Launching Brave Browser: ${bravePath}`);
  // Clean up stale lockfiles to prevent profile lock crashes on rerun
  try {
    for (const lockName of ['SingletonLock', 'SingletonCookie', 'SingletonSocket', 'lockfile']) {
      const lockPath = path.join(profileDir, lockName);
      if (fs.existsSync(lockPath)) {
        fs.unlinkSync(lockPath);
      }
    }
  } catch {
    // Ignore if file is in use
  }

  const context = await chromium.launchPersistentContext(profileDir, {
    executablePath: bravePath,
    headless: sessionConfig.headless ?? false,
    viewport: null, // Maximized / user native window size
    ignoreDefaultArgs: ['--enable-automation'],
    args: [
      '--start-maximized',
      '--disable-blink-features=AutomationControlled',
      '--no-default-browser-check',
      '--disable-infobars'
    ]
  });

  // Automatically accept standard dialogs (e.g. alerts/confirms) unless handled specifically
  context.on('dialog', async (dialog) => {
    console.log(`💬 [PortalSession] Browser Dialog (${dialog.type()}): "${dialog.message()}" -> Auto-accepting`);
    await dialog.accept();
  });

  const page = context.pages()[0] || await context.newPage();
  return { context, page };
}

/**
 * Checks if the current page indicates an active logged-in session.
 */
export async function isUserLoggedIn(page: Page): Promise<boolean> {
  const url = page.url().toLowerCase();
  
  // If we are strictly on auth/registration pages, we are not logged in
  const authPages = ['/public/login', '/public/forgotpassword', '/public/register', '/public/resetpassword'];
  if (authPages.some(p => url.includes(p))) {
    return false;
  }

  try {
    // 1. Explicit positive indicators: Logout link or user profile element
    const logoutLocator = page.locator('#hlkLogout, #cphHeader_hlkLogout, a[href*="Logout"], a[href*="logout"], button:has-text("Logout"), a:has-text("Log Out")');
    if (await logoutLocator.first().isVisible({ timeout: 1000 }).catch(() => false)) {
      return true;
    }

    const userProfileLocator = page.locator('#lblUserName, .user-name, #cphBody_lblUser, #cphHeader_lblUserName, .profile-name');
    if (await userProfileLocator.first().isVisible({ timeout: 1000 }).catch(() => false)) {
      return true;
    }

    // 2. Negative indicator: If public Login button is still visible, definitely not logged in
    const loginLink = page.locator('#hlkLogin, a:has-text("Login")');
    const isLoginVisible = await loginLink.first().isVisible({ timeout: 1000 }).catch(() => false);
    if (isLoginVisible) {
      return false;
    }

    // 3. If URL is deep inside user dashboard or appln forms, we are logged in
    if (url.includes('/user/') || (url.includes('/appln/') && !url.includes('deptservices'))) {
      return true;
    }
  } catch {
    // Locator check timed out or failed
  }

  return false;
}

/**
 * Navigates to GoaOnline Login page and pauses for manual human login.
 * Waits until the user enters credentials + captcha and successfully logs in.
 */
export async function waitForManualLogin(page: Page, timeoutMs: number = 300000): Promise<void> {
  console.log(`🌐 [PortalSession] Checking current portal state...`);
  
  // First check if already logged in from a previous persistent session
  const alreadyLoggedIn = await isUserLoggedIn(page);
  if (alreadyLoggedIn) {
    console.log(`✅ [PortalSession] Persistent session active! User is already logged in.`);
    return;
  }

  // If not on login page, navigate to Login
  if (!page.url().toLowerCase().includes('/public/login')) {
    console.log(`🔗 [PortalSession] Navigating to login page: ${GOA_ONLINE_LOGIN_URL}`);
    await page.goto(GOA_ONLINE_LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  }

  console.log(`\n================================================================`);
  console.log(`🔑 [PortalSession] MANUAL LOGIN REQUIRED`);
  console.log(`👉 Please switch to the opened Brave browser window.`);
  console.log(`👉 Enter your Username/Email, Password, and solve the CAPTCHA.`);
  console.log(`👉 Complete login (and OTP verification if prompted).`);
  console.log(`⏳ The automation is actively waiting for successful login...`);
  console.log(`================================================================\n`);

  const startTime = Date.now();
  const pollIntervalMs = 1000;

  while (Date.now() - startTime < timeoutMs) {
    const currentUrl = page.url().toLowerCase();
    
    // Check if URL changed away from login/auth pages
    const notOnAuthPage = !currentUrl.includes('/public/login') && 
                          !currentUrl.includes('/public/forgot') && 
                          !currentUrl.includes('/public/register') &&
                          currentUrl.includes('goaonline.gov.in');
    
    if (notOnAuthPage) {
      // Allow brief moment for portal redirects to settle
      await page.waitForTimeout(1500);
      const loggedIn = await isUserLoggedIn(page);
      
      if (loggedIn) {
        console.log(`\n🎉 [PortalSession] Successful login detected! Current URL: ${page.url()}`);
        return;
      }
    }

    await page.waitForTimeout(pollIntervalMs);
  }

  throw new Error(`Login timed out after ${timeoutMs / 1000} seconds. User did not complete login.`);
}

/**
 * Navigates to the Residence Certificate service page (REV05) and clicks 'Proceed to Apply'
 * to enter Screen 1 of the application form.
 */
export async function navigateToResidenceService(page: Page): Promise<string> {
  console.log(`\n🚗 [PortalSession] Navigating to Residence Certificate Service (REV05)...`);
  console.log(`🔗 URL: ${RESIDENCE_SERVICE_URL}`);

  await page.goto(RESIDENCE_SERVICE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(1500);

  console.log(`📄 [PortalSession] On service overview page: "${await page.title()}"`);

  // Target the "Proceed to Apply" button
  // Known selector: #cphBody_gvService_lnkProceedApply_0 or text "Proceed to Apply" / "Apply Online"
  const proceedApplyBtn = page.locator(
    '#cphBody_gvService_lnkProceedApply_0, a:has-text("Proceed to Apply"), button:has-text("Proceed to Apply"), a:has-text("Apply Online"), button:has-text("Apply Online"), a:has-text("Apply"), button:has-text("Apply"), input[value*="Apply"], input[value*="Proceed"]'
  ).first();

  console.log(`🔍 [PortalSession] Locating 'Proceed to Apply' button...`);
  await proceedApplyBtn.waitFor({ state: 'visible', timeout: 15000 });

  console.log(`👆 [PortalSession] Clicking 'Proceed to Apply'...`);
  await proceedApplyBtn.click();

  // Handle potential disclaimer / "Continue Anyway" / modal button if it pops up
  try {
    const continueBtn = page.locator(
      '#cphBody_btnCOntinue, input[value*="Continue"], button:has-text("Continue"), button:has-text("I Agree"), button:has-text("Accept")'
    ).first();

    const isContinueVisible = await continueBtn.isVisible({ timeout: 2500 }).catch(() => false);
    if (isContinueVisible) {
      console.log(`ℹ️ [PortalSession] Found disclaimer confirmation button. Clicking to proceed...`);
      await continueBtn.click();
    }
  } catch {
    // No disclaimer popup, proceed normally
  }

  // Wait for the application form (Screen 1) to load
  console.log(`⏳ [PortalSession] Waiting for Residence Application Form (Screen 1) to load...`);
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);

  const finalUrl = page.url();
  console.log(`✅ [PortalSession] Screen 1 reached! Current URL: ${finalUrl}`);
  console.log(`📋 [PortalSession] Page Title: "${await page.title()}"`);

  return finalUrl;
}

/**
 * Complete Phase 1 orchestrator:
 * 1. Launches Brave with persistent profile
 * 2. Waits for manual login
 * 3. Navigates to REV05
 * 4. Clicks Proceed to Apply and reaches Screen 1
 */
export async function startPortalPhase1(sessionConfig: PortalSessionConfig = {}): Promise<PortalSession> {
  const { context, page } = await launchBravePortalContext(sessionConfig);

  // Step 1 & 2: Login handshake
  await waitForManualLogin(page, sessionConfig.loginTimeoutMs);

  // Step 3 & 4: Navigate to REV05 and click Proceed to Apply
  const currentUrl = await navigateToResidenceService(page);

  return {
    context,
    page,
    currentUrl
  };
}
