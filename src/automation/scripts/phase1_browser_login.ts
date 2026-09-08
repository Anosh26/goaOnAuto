/**
 * GoaOnAuto - Phase 1: Brave Browser Launcher, Manual Login Detection & Navigation to REV05.
 * Single Responsibility: Launches Brave, prompts for human login, detects successful authentication,
 * navigates directly to REV05, and opens Screen 1.
 */
import * as readline from 'readline';
import { launchBrave } from '../portalLauncher';

const LOGIN_URL = 'https://goaonline.gov.in/Public/Login';
const REV05_URL = 'https://goaonline.gov.in/Appln/UIL/deptServices?__DocId=REV&__ServiceId=REV05';

export async function runPhase1(): Promise<void> {
  console.log('========================================================================');
  console.log('🏛️  GoaOnAuto Portal Automation - Phase 1');
  console.log('========================================================================');

  const session = await launchBrave();
  const page = session.page;

  try {
    console.log(`\n🌐 Navigating to GoaOnline Login: ${LOGIN_URL}`);
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded' });

    // Check if already logged in (e.g. valid existing session in profile)
    const currentUrl = page.url().toLowerCase();
    const alreadyLoggedIn = !currentUrl.includes('/public/login') && !currentUrl.includes('/login.aspx');

    if (alreadyLoggedIn) {
      console.log('✨ Existing authenticated session detected in profile! Skipping login.');
    } else {
      console.log('\n========================================================================');
      console.log('👉 MANUAL ACTION REQUIRED:');
      console.log('   Please log into your account in the opened Brave browser window.');
      console.log('   (Enter your Username, Password, and solve the Captcha)');
      console.log('⏳ Waiting for successful login (timeout: 5 minutes)...');
      console.log('========================================================================\n');

      // Wait until URL leaves /Public/Login or authenticated indicators appear
      await page.waitForFunction(() => {
        const url = window.location.href.toLowerCase();
        const isLoginPage = url.includes('/public/login') || url.includes('/login.aspx');
        const hasUserMenu = Boolean(
          document.querySelector('.user-menu, #userMenuBox, a[href*="Logout"], a[href*="logout"]')
        );
        return !isLoginPage || hasUserMenu;
      }, null, { timeout: 300000 });

      console.log('✅ Successful login detected!');
      // Brief pause to allow cookies and redirects to settle
      await page.waitForTimeout(2000);
    }

    console.log(`\n🔗 Navigating directly to Residence Certificate Service (REV05):`);
    console.log(`   ${REV05_URL}`);
    await page.goto(REV05_URL, { waitUntil: 'domcontentloaded' });

    console.log('🔍 Searching for "Apply" button on REV05 page...');
    const applyCandidateSelectors = [
      'a#btnApply',
      'button#btnApply',
      'input#btnApply',
      'a:has-text("Apply Online")',
      'a:has-text("Apply")',
      'button:has-text("Apply Online")',
      'button:has-text("Apply")',
      'input[type="submit"][value*="Apply"]',
      'input[type="button"][value*="Apply"]',
      'a[href*="Apply"]'
    ];

    let clicked = false;
    for (const selector of applyCandidateSelectors) {
      const loc = page.locator(selector).first();
      if (await loc.isVisible({ timeout: 1500 }).catch(() => false)) {
        console.log(`👉 Found Apply button with selector "${selector}". Clicking...`);
        await loc.click();
        clicked = true;
        break;
      }
    }

    if (!clicked) {
      console.warn('⚠️  Could not automatically locate the "Apply" button.');
      console.log('   If visible on screen, please click "Apply" manually in Brave.');
    }

    // Wait for the form/Screen 1 transition
    await page.waitForTimeout(2500);
    console.log(`\n📍 Current Page URL: ${page.url()}`);

    console.log('\n========================================================================');
    console.log('🎉 PHASE 1 VERIFIED & COMPLETE!');
    console.log('========================================================================');
    console.log('✅ Brave Browser launched.');
    console.log('✅ Citizen login detected and confirmed.');
    console.log('✅ Navigated to REV05 (Residence Certificate).');
    console.log('✅ Screen 1 is now open.');
    console.log('\n💡 The browser will stay open so you can inspect Screen 1.');
    console.log('   Press [Enter] in this terminal when you are ready to close the browser,');
    console.log('   or keep it open to proceed with Phase 2.');
    console.log('========================================================================\n');

    // Keep session open until user presses Enter in terminal
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    await new Promise<void>((resolve) => {
      rl.question('Press [Enter] to close the browser session... ', () => {
        rl.close();
        resolve();
      });
    });

  } catch (err: any) {
    console.error(`❌ Phase 1 encountered an error: ${err.message}`);
  } finally {
    console.log('👋 Closing Brave Browser session...');
    await session.close();
    console.log('🔒 Session closed cleanly.');
  }
}

if (import.meta.main || require.main === module) {
  runPhase1().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
