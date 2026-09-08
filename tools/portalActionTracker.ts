/**
 * GoaOnAuto Interactive Portal Action Tracker & Blueprint Recorder.
 * Single Responsibility: Injects an unintrusive DOM event listener into Brave browser,
 * intercepts all user clicks, text inputs, dropdown selections, and ASP.NET PostBacks,
 * prints real-time Playwright-ready selectors to the terminal, and exports a clean
 * automation blueprint to recordings/portal_trace_latest.md and JSON.
 */
import * as path from 'path';
import * as fs from 'fs';
import * as readline from 'readline';
import { Page, BrowserContext } from '@playwright/test';
import { launchBravePortalContext, updatePortalStatusOverlay } from '../src/automation/services/portalSessionManager';

export interface RecordedAction {
  index: number;
  timestamp: string;
  eventType: 'click' | 'change' | 'input' | 'navigation';
  pageUrl: string;
  pageTitle: string;
  tag: string;
  id: string;
  name: string;
  inputType?: string;
  label: string;
  textOrValue: string;
  selectedText?: string;
  postBackTarget?: string;
  postBackArgument?: string;
  suggestedSelector: string;
  suggestedPlaywrightCode: string;
}

const RECORDINGS_DIR = path.join(process.cwd(), 'recordings');
if (!fs.existsSync(RECORDINGS_DIR)) {
  fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
}

async function main() {
  console.log('================================================================');
  console.log('🎙️  GOAONAUTO - INTERACTIVE PORTAL ACTION TRACKER');
  console.log('🎯 Scope: Record clicks, inputs, dropdowns & PostBacks in Brave');
  console.log('================================================================\n');

  const sessionTimestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const jsonTracePath = path.join(RECORDINGS_DIR, `portal_trace_${sessionTimestamp}.json`);
  const latestMdPath = path.join(RECORDINGS_DIR, 'portal_trace_latest.md');

  const recordedActions: RecordedAction[] = [];
  let actionCounter = 0;

  const { context, page } = await launchBravePortalContext({
    freshLogin: false // Let user use current session or login naturally
  });

  // Expose recording callback to browser context
  await context.exposeFunction('__goaOnAutoRecordAction', async (rawAction: any) => {
    actionCounter++;
    const action: RecordedAction = {
      index: actionCounter,
      timestamp: new Date().toLocaleTimeString(),
      eventType: rawAction.eventType,
      pageUrl: rawAction.pageUrl || page.url(),
      pageTitle: rawAction.pageTitle || await page.title().catch(() => ''),
      tag: rawAction.tag || '',
      id: rawAction.id || '',
      name: rawAction.name || '',
      inputType: rawAction.inputType || '',
      label: rawAction.label || 'Unlabeled',
      textOrValue: rawAction.textOrValue || '',
      selectedText: rawAction.selectedText || '',
      postBackTarget: rawAction.postBackTarget || '',
      postBackArgument: rawAction.postBackArgument || '',
      suggestedSelector: rawAction.suggestedSelector || '',
      suggestedPlaywrightCode: rawAction.suggestedPlaywrightCode || ''
    };

    recordedActions.push(action);

    // Save progressively to disk
    fs.writeFileSync(jsonTracePath, JSON.stringify(recordedActions, null, 2), 'utf-8');
    generateMarkdownBlueprint(recordedActions, latestMdPath);

    // Terminal formatting
    const eventIcon = 
      action.eventType === 'click' ? '🖱️ CLICK ' :
      action.eventType === 'change' ? '🔽 SELECT' :
      action.eventType === 'input' ? '📝 INPUT ' : '🌐 NAV   ';

    console.log(`\n[#${String(action.index).padStart(3, '0')}] ${eventIcon} | Label: "${action.label}"`);
    console.log(`      Tag: <${action.tag}> | ID: ${action.id ? '#' + action.id : '(none)'} | Name: ${action.name || '(none)'}`);
    if (action.postBackTarget) {
      console.log(`      ⚡ ASP.NET PostBack: ${action.postBackTarget}`);
    }
    if (action.selectedText) {
      console.log(`      🎯 Selected: "${action.selectedText}" (Value: "${action.textOrValue}")`);
    } else if (action.textOrValue && action.eventType !== 'click') {
      console.log(`      ✏️ Value: "${action.textOrValue}"`);
    }
    console.log(`      💻 Code: ${action.suggestedPlaywrightCode}`);

    // Update overlay in browser with live counter
    for (const p of context.pages()) {
      await updatePortalStatusOverlay(
        p,
        `🔴 Tracker Active: ${actionCounter} actions | Last: ${action.label.substring(0, 25)}`,
        'working'
      ).catch(() => {});
    }
  });

  // Inject tracking script into every page and frame
  await context.addInitScript(() => {
    // Helper to find nearest human-readable label
    function findLabelFor(el: HTMLElement): string {
      // 1. Check aria-label or title or placeholder
      if (el.getAttribute('aria-label')) return el.getAttribute('aria-label')!;
      if (el.getAttribute('placeholder')) return el.getAttribute('placeholder')!;
      if (el.getAttribute('title')) return el.getAttribute('title')!;

      // 2. Check <label for="id">
      if (el.id) {
        const label = document.querySelector(`label[for="${el.id}"]`);
        if (label && label.textContent) return label.textContent.trim();
      }

      // 3. Check enclosing label
      const parentLabel = el.closest('label');
      if (parentLabel && parentLabel.textContent) return parentLabel.textContent.trim();

      // 4. Check table structure (ASP.NET forms frequently use <tr><td>Label</td><td><input></td></tr>)
      const td = el.closest('td');
      if (td) {
        const prevTd = td.previousElementSibling;
        if (prevTd && prevTd.textContent && prevTd.textContent.trim().length > 0) {
          return prevTd.textContent.replace(/[*:]/g, '').trim();
        }
      }

      // 5. Fallback: parent div or preceding text
      const parentRow = el.closest('.form-group, .row, p, div');
      if (parentRow) {
        const labelEl = parentRow.querySelector('label, .control-label, span');
        if (labelEl && labelEl.textContent && labelEl.textContent.trim().length > 0) {
          return labelEl.textContent.replace(/[*:]/g, '').trim();
        }
      }

      // 6. If link or button, use text content
      if (el.tagName.toLowerCase() === 'a' || el.tagName.toLowerCase() === 'button' || (el as HTMLInputElement).type === 'submit') {
        const text = el.textContent?.trim() || (el as HTMLInputElement).value;
        if (text && text.length > 0) return text;
      }

      return el.id || el.getAttribute('name') || el.tagName.toLowerCase();
    }

    // Helper to extract ASP.NET __doPostBack target
    function getPostBackInfo(el: HTMLElement): { target?: string; arg?: string } {
      const href = el.getAttribute('href') || '';
      const onclick = el.getAttribute('onclick') || '';
      const combined = href + ' ' + onclick;

      const match = combined.match(/__doPostBack\s*\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]*)['"]\s*\)/);
      if (match && match[1]) {
        return { target: match[1], arg: match[2] || '' };
      }
      return {};
    }

    // Helper to generate best Playwright selector and code snippet
    function generateSelectorAndCode(el: HTMLElement, eventType: string, val: string, selectedText?: string): { selector: string; code: string } {
      const tag = el.tagName.toLowerCase();
      const id = el.id;
      const name = el.getAttribute('name');
      const text = el.textContent?.trim() || '';
      const postBack = getPostBackInfo(el);

      let selector = '';
      let code = '';

      if (postBack.target) {
        selector = `a[href*="${postBack.target}"]`;
        code = `await page.locator('${selector}').click();`;
      } else if (id) {
        selector = `#${id}`;
        if (eventType === 'click') {
          code = `await page.locator('${selector}').click();`;
        } else if (eventType === 'change' && tag === 'select') {
          code = `await page.selectOption('${selector}', '${val}'); // ${selectedText || ''}`;
        } else if (eventType === 'input' || eventType === 'change') {
          code = `await page.fill('${selector}', '${val}');`;
        }
      } else if (name) {
        selector = `[name="${name}"]`;
        if (eventType === 'click') {
          code = `await page.locator('${selector}').click();`;
        } else if (tag === 'select') {
          code = `await page.selectOption('${selector}', '${val}');`;
        } else {
          code = `await page.fill('${selector}', '${val}');`;
        }
      } else if (text && text.length < 30) {
        selector = `${tag}:has-text("${text}")`;
        code = `await page.locator('${selector}').click();`;
      } else {
        selector = `${tag}`;
        code = `await page.locator('${selector}').click();`;
      }

      return { selector, code };
    }

    // Visual pulse effect on interactive click
    function highlightElement(el: HTMLElement) {
      const origOutline = el.style.outline;
      const origBoxShadow = el.style.boxShadow;
      el.style.outline = '3px solid #50fa7b';
      el.style.boxShadow = '0 0 12px #50fa7b';
      setTimeout(() => {
        el.style.outline = origOutline;
        el.style.boxShadow = origBoxShadow;
      }, 700);
    }

    // Listen to CLICKS (capture phase)
    window.addEventListener('click', (e) => {
      const target = (e.target as HTMLElement).closest('a, button, input, select, textarea, [role="button"]') as HTMLElement || e.target as HTMLElement;
      if (!target || target.id === 'goaonauto-status-pill') return;

      highlightElement(target);

      const postBack = getPostBackInfo(target);
      const tag = target.tagName.toLowerCase();
      const inputEl = target as HTMLInputElement;
      const label = findLabelFor(target);
      const textVal = target.textContent?.trim() || inputEl.value || '';

      const { selector, code } = generateSelectorAndCode(target, 'click', textVal);

      // @ts-ignore
      window.__goaOnAutoRecordAction({
        eventType: 'click',
        pageUrl: window.location.href,
        pageTitle: document.title,
        tag,
        id: target.id || '',
        name: target.getAttribute('name') || '',
        inputType: inputEl.type || '',
        label,
        textOrValue: textVal,
        postBackTarget: postBack.target || '',
        postBackArgument: postBack.arg || '',
        suggestedSelector: selector,
        suggestedPlaywrightCode: code
      });
    }, true);

    // Listen to SELECT DROPDOWN CHANGES
    window.addEventListener('change', (e) => {
      const target = e.target as HTMLElement;
      if (!target) return;

      const tag = target.tagName.toLowerCase();
      const label = findLabelFor(target);

      if (tag === 'select') {
        const select = target as HTMLSelectElement;
        const selectedOpt = select.selectedOptions[0];
        const val = select.value;
        const selectedText = selectedOpt ? selectedOpt.text.trim() : '';
        const { selector, code } = generateSelectorAndCode(target, 'change', val, selectedText);

        // @ts-ignore
        window.__goaOnAutoRecordAction({
          eventType: 'change',
          pageUrl: window.location.href,
          pageTitle: document.title,
          tag: 'select',
          id: target.id || '',
          name: target.getAttribute('name') || '',
          label,
          textOrValue: val,
          selectedText,
          suggestedSelector: selector,
          suggestedPlaywrightCode: code
        });
      } else if (tag === 'input' && ((target as HTMLInputElement).type === 'checkbox' || (target as HTMLInputElement).type === 'radio')) {
        const input = target as HTMLInputElement;
        const { selector, code } = generateSelectorAndCode(target, 'click', input.checked ? 'checked' : 'unchecked');
        // @ts-ignore
        window.__goaOnAutoRecordAction({
          eventType: 'change',
          pageUrl: window.location.href,
          pageTitle: document.title,
          tag: 'input',
          id: target.id || '',
          name: target.getAttribute('name') || '',
          inputType: input.type,
          label,
          textOrValue: input.checked ? 'true' : 'false',
          suggestedSelector: selector,
          suggestedPlaywrightCode: input.checked ? `await page.check('${selector}');` : `await page.uncheck('${selector}');`
        });
      }
    }, true);

    // Debounced INPUT recorder for typing
    let inputTimeout: any = null;
    window.addEventListener('input', (e) => {
      const target = e.target as HTMLInputElement | HTMLTextAreaElement;
      if (!target || target.tagName.toLowerCase() === 'select') return;

      clearTimeout(inputTimeout);
      inputTimeout = setTimeout(() => {
        const label = findLabelFor(target);
        const val = target.value;
        const { selector, code } = generateSelectorAndCode(target, 'input', val);

        // @ts-ignore
        window.__goaOnAutoRecordAction({
          eventType: 'input',
          pageUrl: window.location.href,
          pageTitle: document.title,
          tag: target.tagName.toLowerCase(),
          id: target.id || '',
          name: target.getAttribute('name') || '',
          inputType: (target as HTMLInputElement).type || '',
          label,
          textOrValue: val,
          suggestedSelector: selector,
          suggestedPlaywrightCode: code
        });
      }, 750);
    }, true);
  });

  // Navigate to login page to start session
  console.log('🌐 Opening GoaOnline in Brave...');
  await page.goto('https://goaonline.gov.in/Public/Login', { waitUntil: 'domcontentloaded' }).catch(() => {});

  await updatePortalStatusOverlay(
    page,
    '🔴 GoaOnAuto Tracker Active — Monitoring all interactions...',
    'waiting'
  );

  console.log('\n================================================================');
  console.log('🔴 TRACKER IS LIVE IN BRAVE!');
  console.log('👉 Interact with the portal naturally in the opened Brave window.');
  console.log('👉 Every click, input, dropdown, and PostBack will be printed here.');
  console.log('👉 Blueprint will be continuously saved to:');
  console.log(`   📄 ${latestMdPath}`);
  console.log('⌨️  Press [ENTER] in this terminal whenever you wish to finish.');
  console.log('================================================================\n');

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

  console.log('\n================================================================');
  console.log(`🎉 RECORDING FINISHED! Captured ${recordedActions.length} actions.`);
  console.log(`💾 JSON Trace: ${jsonTracePath}`);
  console.log(`📄 Markdown Blueprint: ${latestMdPath}`);
  console.log('================================================================');

  await context.close().catch(() => {});
  process.exit(0);
}

function generateMarkdownBlueprint(actions: RecordedAction[], outputPath: string): void {
  let md = '# GoaOnline Portal Recorded Action Blueprint\n\n';
  md += `*Captured ${actions.length} user actions on ${new Date().toLocaleString()}*\n\n`;

  md += '## Playwright Automation Code Snippet\n\n```typescript\n';
  for (const a of actions) {
    md += `// [Step ${a.index}] ${a.label} (${a.eventType})\n`;
    md += `${a.suggestedPlaywrightCode}\n`;
    if (a.postBackTarget) {
      md += `await page.waitForLoadState('domcontentloaded');\n`;
    }
  }
  md += '```\n\n';

  md += '## Detailed Action Log\n\n';
  md += '| # | Event | Field Label | Control ID | Tag / Type | Value / PostBack |\n';
  md += '|---|---|---|---|---|---|\n';
  for (const a of actions) {
    const val = a.postBackTarget || a.selectedText || a.textOrValue || '-';
    md += `| ${a.index} | **${a.eventType.toUpperCase()}** | ${a.label} | \`${a.id || a.name || '-'}\` | \`<${a.tag}>\` | \`${val.substring(0, 40)}\` |\n`;
  }

  fs.writeFileSync(outputPath, md, 'utf-8');
}

main().catch(err => {
  console.error('❌ Tracker error:', err);
  process.exit(1);
});
