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
  freshLogin?: boolean;
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
 * Strictly checks for positive citizen session indicators (e.g. Logout button, user profile).
 * NEVER assumes a user is logged in just because a URL is on goaonline.gov.in.
 */
export async function isUserLoggedIn(page: Page): Promise<boolean> {
  const url = page.url().toLowerCase();
  
  // 1. If on auth pages, public login, or blank tab -> definitely NOT logged in
  const authPages = ['/public/login', '/public/forgotpassword', '/public/register', '/public/resetpassword'];
  if (authPages.some(p => url.includes(p)) || url === 'about:blank') {
    return false;
  }

  if (!url.includes('goaonline.gov.in')) {
    return false;
  }

  // 2. If password field is present anywhere on the page -> NOT logged in
  try {
    if (await page.locator('input[type="password"]').count() > 0) {
      return false;
    }
  } catch {
    // Ignore locator error
  }

  // 3. If "Login" or "Register" link is present in header -> NOT logged in
  try {
    const loginLink = page.locator('#hlkLogin, #cphHeader_hlkLogin, a[href*="/Public/Login" i]');
    if (await loginLink.count() > 0) {
      return false;
    }
  } catch {
    // Ignore locator error
  }

  // 4. Positive check: Logout button or user profile indicator in DOM
  try {
    const logoutIndicators = page.locator(
      '#hlkLogout, #cphHeader_hlkLogout, a[href*="Logout" i], a[href*="logout" i], #cphHeader_lblUserName, #cphBody_lblUser, .profile-name, .user-name, #userMenuBox'
    );
    if (await logoutIndicators.count() > 0) {
      return true;
    }
  } catch {
    // Ignore locator error
  }

  // 5. Positive check: ASPXAUTH cookie on authenticated citizen pages (e.g., /User/, /Appln/)
  // Note: /Appln/UIL/deptServices is a public overview page, not proof of authentication.
  try {
    const cookies = await page.context().cookies();
    const hasAuthCookie = cookies.some(c => 
      c.domain.includes('goaonline') && 
      (c.name.includes('ASPXAUTH') || c.name.includes('.ASPXAUTH') || c.name.includes('AuthToken')) &&
      c.value.length > 20
    );

    const isCitizenAuthenticatedPage = (url.includes('/user/') || url.includes('/dashboard')) && !url.includes('/deptservices');
    if (hasAuthCookie && isCitizenAuthenticatedPage) {
      return true;
    }
  } catch {
    // Ignore cookie check error
  }

  return false;
}

/**
 * Injects or updates a lightweight, non-intrusive status pill overlay in the browser.
 * Styled in GoaOnAuto Dracula theme, pointer-events: none, positioned top-right.
 * NEVER modifies form elements, inputs, or scripts, preserving portal integrity.
 */
export async function updatePortalStatusOverlay(
  page: Page,
  message: string,
  type: 'info' | 'waiting' | 'working' | 'success' = 'info'
): Promise<void> {
  try {
    if (page.isClosed()) return;
    await page.evaluate(({ msg, type }) => {
      let pill = document.getElementById('goaonauto-status-pill');
      if (!pill) {
        pill = document.createElement('div');
        pill.id = 'goaonauto-status-pill';
        pill.style.position = 'fixed';
        pill.style.top = '16px';
        pill.style.right = '24px';
        pill.style.zIndex = '2147483647';
        pill.style.padding = '10px 20px';
        pill.style.borderRadius = '24px';
        pill.style.fontSize = '14px';
        pill.style.fontWeight = '600';
        pill.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        pill.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.4)';
        pill.style.pointerEvents = 'none';
        pill.style.userSelect = 'none';
        pill.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
        pill.style.display = 'flex';
        pill.style.alignItems = 'center';
        pill.style.gap = '8px';
        document.body.appendChild(pill);
      }

      const styles = {
        info: { bg: '#282a36', text: '#f8f8f2', border: '#bd93f9', dot: '#bd93f9' },
        waiting: { bg: '#282a36', text: '#f1fa8c', border: '#ffb86c', dot: '#ffb86c' },
        working: { bg: '#282a36', text: '#8be9fd', border: '#8be9fd', dot: '#8be9fd' },
        success: { bg: '#282a36', text: '#50fa7b', border: '#50fa7b', dot: '#50fa7b' }
      };
      const s = styles[type] || styles.info;
      pill.style.backgroundColor = s.bg;
      pill.style.color = s.text;
      pill.style.border = `2px solid ${s.border}`;
      pill.innerHTML = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:${s.dot};margin-right:6px;"></span>${msg}`;
    }, { msg: message, type });
  } catch {
    // Graceful fallback if DOM is navigating
  }
}

/**
 * Navigates to GoaOnline Login page and pauses for manual human login.
 * Actively monitors all tabs for successful authentication.
 * Returns the active authenticated Page.
 */
export async function waitForManualLogin(page: Page, configOrTimeout: PortalSessionConfig | number = {}): Promise<Page> {
  const sessionConfig: PortalSessionConfig = typeof configOrTimeout === 'number'
    ? { loginTimeoutMs: configOrTimeout }
    : configOrTimeout;

  const timeoutMs = sessionConfig.loginTimeoutMs ?? 300000;
  const isFresh = sessionConfig.freshLogin ?? true;

  if (isFresh) {
    console.log(`🧹 [PortalSession] Clearing cookies to guarantee fresh manual login prompt...`);
    await page.context().clearCookies().catch(() => {});
  }

  console.log(`🔗 [PortalSession] Navigating to GoaOnline login page: ${GOA_ONLINE_LOGIN_URL}`);
  try {
    await page.goto(GOA_ONLINE_LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  } catch (e: any) {
    console.warn(`⚠️ [PortalSession] Navigation retry notice: ${e.message}`);
    await page.goto(GOA_ONLINE_LOGIN_URL, { timeout: 30000 }).catch(() => {});
  }
  await page.waitForTimeout(1000);

  // If not a fresh login request, check if the portal redirected to a logged-in dashboard
  if (!isFresh) {
    const alreadyLoggedIn = await isUserLoggedIn(page);
    if (alreadyLoggedIn) {
      console.log(`✅ [PortalSession] Active session detected! User is already logged in.`);
      await updatePortalStatusOverlay(page, 'GoaOnAuto: Active session detected! Navigating to REV05...', 'success');
      return page;
    }
  }

  await updatePortalStatusOverlay(page, 'GoaOnAuto: Please log in manually (waiting for credentials/captcha)...', 'waiting');

  console.log(`\n================================================================`);
  console.log(`🔑 [PortalSession] MANUAL LOGIN REQUIRED`);
  console.log(`👉 Switch to the opened Brave browser window.`);
  console.log(`👉 Enter your Username/Email, Password, and solve the CAPTCHA.`);
  console.log(`👉 Click Login (complete OTP verification if prompted).`);
  console.log(`⏳ The automation is actively monitoring for successful login...`);
  console.log(`================================================================\n`);

  const startTime = Date.now();
  const pollIntervalMs = 1000;

  while (Date.now() - startTime < timeoutMs) {
    // Check all open tabs in context in case the user opened a new tab or logged in there
    const allPages = page.context().pages();
    for (const p of allPages) {
      const pUrl = p.url().toLowerCase();
      // Must be on goaonline and MUST have navigated away from /public/login
      if (pUrl.includes('goaonline.gov.in') && !pUrl.includes('/public/login') && !pUrl.includes('/public/forgotpassword') && pUrl !== 'about:blank') {
        const loggedIn = await isUserLoggedIn(p);
        if (loggedIn) {
          console.log(`\n🎉 [PortalSession] Successful login detected! Current URL: ${p.url()}`);
          await p.bringToFront();
          await updatePortalStatusOverlay(p, 'GoaOnAuto: Login verified! Navigating to Residence Service (REV05)...', 'success');
          return p;
        }
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
export async function navigateToResidenceService(page: Page): Promise<{ formPage: Page; currentUrl: string }> {
  console.log(`\n🚗 [PortalSession] Navigating to Residence Certificate Service (REV05)...`);
  console.log(`🔗 URL: ${RESIDENCE_SERVICE_URL}`);

  // Find active GoaOnline page or use default
  const activePage = page.context().pages().find(p => p.url().toLowerCase().includes('goaonline.gov.in')) || page;
  await activePage.bringToFront();

  await activePage.goto(RESIDENCE_SERVICE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await activePage.waitForTimeout(1500);

  await updatePortalStatusOverlay(activePage, 'GoaOnAuto: Residence Service (REV05) -> Clicking "Proceed to Apply"...', 'working');
  console.log(`📄 [PortalSession] On service overview page: "${await activePage.title()}"`);

  // Target the "Proceed to Apply" button using the exact ASP.NET GridView doPostBack target
  const proceedApplyBtn = activePage.locator([
    'a[href*="ctl00$cphBody$gvService$ctl02$lnkProceedApply"]',
    '#ctl00_cphBody_gvService_ctl02_lnkProceedApply',
    'a[id*="lnkProceedApply"]',
    'a[href*="lnkProceedApply"]',
    'a:has-text("Proceed to Apply")',
    'a:has-text("Apply Online")',
    'a:has-text("Apply")',
    'button:has-text("Proceed to Apply")',
    'input[value*="Proceed"]',
    'input[value*="Apply"]'
  ].join(', ')).first();

  console.log(`🔍 [PortalSession] Locating 'Proceed to Apply' button...`);
  const isFound = await proceedApplyBtn.waitFor({ state: 'visible', timeout: 10000 }).then(() => true).catch(() => false);

  console.log(`👆 [PortalSession] Triggering 'Proceed to Apply'...`);
  
  // Watch for potential popup / new tab if opened in separate target
  const [newPage] = await Promise.all([
    activePage.context().waitForEvent('page', { timeout: 4000 }).catch(() => null),
    (async () => {
      if (isFound) {
        try {
          await proceedApplyBtn.click({ timeout: 5000 });
          return;
        } catch (err: any) {
          console.warn(`Direct click failed (${err.message}). Invoking __doPostBack fallback...`);
        }
      }
      // Direct ASP.NET WebForms __doPostBack trigger
      await activePage.evaluate(() => {
        // @ts-ignore
        if (typeof window.__doPostBack === 'function') {
          // @ts-ignore
          window.__doPostBack('ctl00$cphBody$gvService$ctl02$lnkProceedApply', '');
        } else {
          const el = document.querySelector('a[href*="lnkProceedApply"]') as HTMLElement;
          if (el) el.click();
        }
      }).catch((e: any) => console.warn('doPostBack dispatch notice:', e.message));
    })()
  ]);

  const formPage = newPage || activePage;
  await formPage.bringToFront();

  // Handle potential disclaimer / "Continue Anyway" / modal button if it pops up
  try {
    const continueBtn = formPage.locator(
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
  await formPage.waitForLoadState('domcontentloaded');
  await formPage.waitForTimeout(2000);

  const finalUrl = formPage.url();
  console.log(`✅ [PortalSession] Screen 1 reached! Current URL: ${finalUrl}`);
  console.log(`📋 [PortalSession] Page Title: "${await formPage.title()}"`);

  await updatePortalStatusOverlay(formPage, '✨ GoaOnAuto: Residence Form Screen 1 Loaded!', 'success');

  return { formPage, currentUrl: finalUrl };
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
  const activePage = await waitForManualLogin(page, sessionConfig);

  // Step 3 & 4: Navigate to REV05 and click Proceed to Apply
  const { formPage, currentUrl } = await navigateToResidenceService(activePage);

  return {
    context,
    page: formPage,
    currentUrl
  };
}

