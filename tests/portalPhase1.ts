/**
 * Phase 1 Integration Test & Verification Runner.
 * Executes:
 * 1. Launches Brave with dedicated persistent profile
 * 2. Pauses for manual human login on GoaOnline
 * 3. Navigates to REV05 Residence Certificate service
 * 4. Clicks 'Proceed to Apply' and arrives on Screen 1
 * 5. Inspects and prints all detected input fields on Screen 1 for Phase 2 preparation
 * 6. Keeps browser open for human inspection
 */
import * as readline from 'readline';
import { startPortalPhase1 } from '../src/automation/services/portalSessionManager';

async function runPhase1() {
  console.log('================================================================');
  console.log('🏛️  GOAONAUTO - PORTAL AUTOMATION: PHASE 1 TEST');
  console.log('🎯 Scope: Brave Launch -> Manual Login -> REV05 -> Screen 1');
  console.log('================================================================\n');

  try {
    const session = await startPortalPhase1({
      loginTimeoutMs: 300000 // 5 minutes for user to log in
    });

    console.log('\n================================================================');
    console.log('🎉 PHASE 1 VERIFICATION SUCCESSFUL!');
    console.log(`🌐 Final Screen 1 URL: ${session.currentUrl}`);
    console.log(`📄 Page Title: "${await session.page.title()}"`);
    console.log('================================================================\n');

    // Inspect Screen 1 form fields to aid Phase 2 development
    console.log('🔍 Inspecting Screen 1 interactive elements:');
    const fields = await session.page.locator('input, select, textarea').evaluateAll((elements) => {
      return elements.map((el) => {
        const inputEl = el as HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;
        return {
          tag: el.tagName.toLowerCase(),
          id: inputEl.id || '',
          name: inputEl.name || '',
          type: (el as HTMLInputElement).type || '',
          placeholder: (el as HTMLInputElement).placeholder || '',
          value: inputEl.value || ''
        };
      }).filter(f => f.id || f.name);
    });

    console.log(`📋 Found ${fields.length} form controls on Screen 1:`);
    fields.forEach((f, idx) => {
      console.log(`   [${idx + 1}] <${f.tag}> id="${f.id}" name="${f.name}" type="${f.type}"`);
    });

    console.log('\n================================================================');
    console.log('👀 Brave browser is open on Screen 1 for your inspection.');
    console.log('⌨️  Press ENTER in this terminal when you are ready to exit.');
    console.log('================================================================');

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
    await session.context.close();
    console.log('✅ Phase 1 completed cleanly.');
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Phase 1 Error:', error);
    process.exit(1);
  }
}

runPhase1();
