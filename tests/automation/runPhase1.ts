import * as readline from 'readline';
import { setupTestSession, teardownTestSession } from './baseTest';

async function runModularPhase1() {
  console.log('================================================================');
  console.log('🏛️  GOAONAUTO - MODULAR TEST: RESIDENCE PHASE 1');
  console.log('🎯 Scope: Login -> REV05 -> Proceed to Apply -> Screen 1 Fields');
  console.log('================================================================\n');

  try {
    const keepSession = process.argv.includes('--keep-session');
    
    // 1. Setup session and inject visual tracker
    const session = await setupTestSession('phase1_test', {
      loginTimeoutMs: 300000,
      freshLogin: !keepSession
    });

    console.log('\n================================================================');
    console.log('🎉 PHASE 1 VERIFICATION SUCCESSFUL!');
    console.log(`🌐 Final Screen 1 URL: ${session.currentUrl}`);
    console.log(`📄 Page Title: "${await session.page.title()}"`);
    console.log('================================================================\n');

    // 2. Inspect Screen 1 form fields to aid Phase 2 development
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

    await teardownTestSession(session);
    process.exit(0);
  } catch (error) {
    console.error('\n❌ Phase 1 Error:', error);
    process.exit(1);
  }
}

runModularPhase1();
