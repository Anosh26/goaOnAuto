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

  // Inject tracking logic as a standalone function
  const injectTrackerScript = `(() => {
    if (window.__goaOnAutoInjected) return;
    window.__goaOnAutoInjected = true;

    function ensureStatusPill(text) {
      try {
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
          pill.style.backgroundColor = '#282a36';
          pill.style.color = '#50fa7b';
          pill.style.border = '2px solid #50fa7b';
          pill.style.display = 'flex';
          pill.style.alignItems = 'center';
          pill.style.gap = '8px';
          pill.style.transition = 'all 0.3s ease';
          if (document.body) {
            document.body.appendChild(pill);
          } else {
            document.addEventListener('DOMContentLoaded', () => {
              if (document.body && !document.getElementById('goaonauto-status-pill')) {
                document.body.appendChild(pill);
              }
            });
          }
        }
        if (pill) {
          pill.innerHTML = '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:#50fa7b;margin-right:6px;"></span>' + (text || '🔴 GoaOnAuto Tracker Active');
        }
      } catch (e) {}
    }

    ensureStatusPill('🔴 GoaOnAuto Tracker Active');

    function findLabelFor(el) {
      if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
      if (el.getAttribute('placeholder')) return el.getAttribute('placeholder');
      if (el.getAttribute('title')) return el.getAttribute('title');

      if (el.id) {
        const label = document.querySelector('label[for="' + el.id + '"]');
        if (label && label.textContent) return label.textContent.trim();
      }

      const parentLabel = el.closest('label');
      if (parentLabel && parentLabel.textContent) return parentLabel.textContent.trim();

      const td = el.closest('td');
      if (td) {
        const prevTd = td.previousElementSibling;
        if (prevTd && prevTd.textContent && prevTd.textContent.trim().length > 0) {
          return prevTd.textContent.replace(/[*:]/g, '').trim();
        }
      }

      const parentRow = el.closest('.form-group, .row, p, div');
      if (parentRow) {
        const labelEl = parentRow.querySelector('label, .control-label, span');
        if (labelEl && labelEl.textContent && labelEl.textContent.trim().length > 0) {
          return labelEl.textContent.replace(/[*:]/g, '').trim();
        }
      }

      if (el.tagName.toLowerCase() === 'a' || el.tagName.toLowerCase() === 'button' || el.type === 'submit') {
        const text = el.textContent?.trim() || el.value;
        if (text && text.length > 0) return text;
      }

      return el.id || el.getAttribute('name') || el.tagName.toLowerCase();
    }

    function getPostBackInfo(el) {
      const href = el.getAttribute('href') || '';
      const onclick = el.getAttribute('onclick') || '';
      const combined = href + ' ' + onclick;
      const match = combined.match(/__doPostBack\\s*\\(\\s*['"]([^'"]+)['"]\\s*,\\s*['"]([^'"]*)['"]\\s*\\)/);
      if (match && match[1]) {
        return { target: match[1], arg: match[2] || '' };
      }
      return {};
    }

    function generateSelectorAndCode(el, eventType, val, selectedText) {
      const tag = el.tagName.toLowerCase();
      const id = el.id;
      const name = el.getAttribute('name');
      const text = el.textContent?.trim() || '';
      const postBack = getPostBackInfo(el);

      let selector = '';
      let code = '';

      if (postBack.target) {
        selector = 'a[href*="' + postBack.target + '"]';
        code = "await page.locator('" + selector + "').click();";
      } else if (id) {
        selector = '#' + id;
        if (eventType === 'click') {
          code = "await page.locator('" + selector + "').click();";
        } else if (eventType === 'change' && tag === 'select') {
          code = "await page.selectOption('" + selector + "', '" + val + "'); // " + (selectedText || '');
        } else if (eventType === 'input' || eventType === 'change') {
          code = "await page.fill('" + selector + "', '" + val + "');";
        }
      } else if (name) {
        selector = '[name="' + name + '"]';
        if (eventType === 'click') {
          code = "await page.locator('" + selector + "').click();";
        } else if (tag === 'select') {
          code = "await page.selectOption('" + selector + "', '" + val + "');";
        } else {
          code = "await page.fill('" + selector + "', '" + val + "');";
        }
      } else if (text && text.length < 30) {
        selector = tag + ':has-text("' + text + '")';
        code = "await page.locator('" + selector + "').click();";
      } else {
        selector = tag;
        code = "await page.locator('" + selector + "').click();";
      }

      return { selector, code };
    }

    function highlightElement(el) {
      const origOutline = el.style.outline;
      const origBoxShadow = el.style.boxShadow;
      el.style.outline = '3px solid #50fa7b';
      el.style.boxShadow = '0 0 12px #50fa7b';
      setTimeout(() => {
        el.style.outline = origOutline;
        el.style.boxShadow = origBoxShadow;
      }, 700);
    }

    // CLICKS
    window.addEventListener('click', (e) => {
      const target = e.target.closest('a, button, input, select, textarea, [role="button"]') || e.target;
      if (!target || target.id === 'goaonauto-status-pill') return;

      highlightElement(target);

      const postBack = getPostBackInfo(target);
      const tag = target.tagName.toLowerCase();
      const label = findLabelFor(target);
      const textVal = target.textContent?.trim() || target.value || '';
      const { selector, code } = generateSelectorAndCode(target, 'click', textVal);

      ensureStatusPill('🖱️ Click: ' + (label.substring(0, 20) || tag));

      if (window.__goaOnAutoRecordAction) {
        window.__goaOnAutoRecordAction({
          eventType: 'click',
          pageUrl: window.location.href,
          pageTitle: document.title,
          tag,
          id: target.id || '',
          name: target.getAttribute('name') || '',
          inputType: target.type || '',
          label,
          textOrValue: textVal,
          postBackTarget: postBack.target || '',
          postBackArgument: postBack.arg || '',
          suggestedSelector: selector,
          suggestedPlaywrightCode: code
        });
      }
    }, true);

    // DROPDOWNS & CHECKBOXES & FILES
    window.addEventListener('change', (e) => {
      const target = e.target;
      if (!target) return;

      const tag = target.tagName.toLowerCase();
      const label = findLabelFor(target);

      if (tag === 'select') {
        const selectedOpt = target.selectedOptions ? target.selectedOptions[0] : null;
        const val = target.value;
        const selectedText = selectedOpt ? selectedOpt.text.trim() : '';
        const { selector, code } = generateSelectorAndCode(target, 'change', val, selectedText);

        ensureStatusPill('🔽 Selected: ' + (selectedText.substring(0, 20) || val));

        if (window.__goaOnAutoRecordAction) {
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
        }
      } else if (tag === 'input' && (target.type === 'checkbox' || target.type === 'radio')) {
        const { selector } = generateSelectorAndCode(target, 'click', target.checked ? 'checked' : 'unchecked');
        ensureStatusPill('☑️ ' + (label.substring(0, 20) || 'Check'));

        if (window.__goaOnAutoRecordAction) {
          window.__goaOnAutoRecordAction({
            eventType: 'change',
            pageUrl: window.location.href,
            pageTitle: document.title,
            tag: 'input',
            id: target.id || '',
            name: target.getAttribute('name') || '',
            inputType: target.type,
            label,
            textOrValue: target.checked ? 'true' : 'false',
            suggestedSelector: selector,
            suggestedPlaywrightCode: target.checked ? "await page.check('" + selector + "');" : "await page.uncheck('" + selector + "');"
          });
        }
      } else if (tag === 'input' && target.type === 'file') {
        const fileName = target.files && target.files[0] ? target.files[0].name : '';
        const { selector } = generateSelectorAndCode(target, 'change', fileName);
        ensureStatusPill('📁 File: ' + (fileName.substring(0, 20) || 'Upload'));

        if (window.__goaOnAutoRecordAction) {
          window.__goaOnAutoRecordAction({
            eventType: 'change',
            pageUrl: window.location.href,
            pageTitle: document.title,
            tag: 'input',
            id: target.id || '',
            name: target.getAttribute('name') || '',
            inputType: 'file',
            label,
            textOrValue: fileName,
            suggestedSelector: selector,
            suggestedPlaywrightCode: "await page.setInputFiles('" + selector + "', 'path/to/" + (fileName || 'document.pdf') + "');"
          });
        }
      }
    }, true);

    // INPUT & BLUR
    window.addEventListener('blur', (e) => {
      const target = e.target;
      if (!target || !target.tagName) return;
      const tag = target.tagName.toLowerCase();
      const inputType = target.type || '';
      if ((tag === 'input' && inputType !== 'button' && inputType !== 'submit' && inputType !== 'file' && inputType !== 'checkbox' && inputType !== 'radio') || tag === 'textarea') {
        const val = target.value;
        if (!val) return;
        const label = findLabelFor(target);
        const { selector, code } = generateSelectorAndCode(target, 'input', val);

        if (window.__goaOnAutoRecordAction) {
          window.__goaOnAutoRecordAction({
            eventType: 'input',
            pageUrl: window.location.href,
            pageTitle: document.title,
            tag,
            id: target.id || '',
            name: target.getAttribute('name') || '',
            inputType,
            label,
            textOrValue: val,
            suggestedSelector: selector,
            suggestedPlaywrightCode: code
          });
        }
      }
    }, true);

    let inputTimeout = null;
    window.addEventListener('input', (e) => {
      const target = e.target;
      if (!target || target.tagName.toLowerCase() === 'select') return;

      clearTimeout(inputTimeout);
      inputTimeout = setTimeout(() => {
        const label = findLabelFor(target);
        const val = target.value;
        const { selector, code } = generateSelectorAndCode(target, 'input', val);

        ensureStatusPill('✏️ ' + (label.substring(0, 20) || 'Input'));

        if (window.__goaOnAutoRecordAction) {
          window.__goaOnAutoRecordAction({
            eventType: 'input',
            pageUrl: window.location.href,
            pageTitle: document.title,
            tag: target.tagName.toLowerCase(),
            id: target.id || '',
            name: target.getAttribute('name') || '',
            inputType: target.type || '',
            label,
            textOrValue: val,
            suggestedSelector: selector,
            suggestedPlaywrightCode: code
          });
        }
      }, 750);
    }, true);
  })();`;

  // 1. Add init script for all future documents & frames
  await context.addInitScript(injectTrackerScript);

  // 2. Inject immediately into all existing pages right now
  const attachToPage = async (p: Page) => {
    try {
      await p.evaluate(injectTrackerScript).catch(() => {});
    } catch {}

    p.on('domcontentloaded', async () => {
      await p.evaluate(injectTrackerScript).catch(() => {});
    });

    p.on('framenavigated', async (frame) => {
      if (frame === p.mainFrame()) {
        const url = frame.url();
        if (!url || url === 'about:blank') return;
        const title = await p.title().catch(() => '');
        console.log(`\n🌐 [PAGE NAVIGATED] -> ${url}`);
        if (title) console.log(`      Title: "${title}"`);
        await p.evaluate(injectTrackerScript).catch(() => {});
      }
    });
  };

  for (const p of context.pages()) {
    await attachToPage(p);
  }

  context.on('page', async (newPage) => {
    console.log(`\n📑 [NEW TAB DETECTED]`);
    await attachToPage(newPage);
  });

  // Navigate if on blank page (non-blocking)
  const activeUrl = page.url();
  await page.bringToFront().catch(() => {});

  if (activeUrl === 'about:blank' || activeUrl === '') {
    console.log('🌐 Opening GoaOnline login page...');
    await page.goto('https://goaonline.gov.in/Public/Login', { timeout: 30000, waitUntil: 'domcontentloaded' }).catch(e => {
      console.log('Navigation notice: ' + e.message);
    });
  } else {
    console.log(`🌐 Attached to active tab: ${activeUrl}`);
  }

  console.log('\n================================================================');
  console.log('🔴 TRACKER IS LIVE IN BRAVE!');
  console.log('👉 You should see a green "🔴 GoaOnAuto Tracker Active" badge at the top-right.');
  console.log('👉 Interact with the portal naturally in Brave.');
  console.log('👉 Every click, input, dropdown, and PostBack is being captured.');
  console.log(`👉 Blueprint saving to: recordings/portal_trace_latest.md`);
  console.log('⌨️  Press [ENTER] in this terminal whenever you are ready to finish.');
  console.log('================================================================\n');

  // Multi-mode stdin listener to guarantee ENTER works on Windows PowerShell & Bun
  await new Promise<void>((resolve) => {
    let resolved = false;
    const finish = () => {
      if (!resolved) {
        resolved = true;
        resolve();
      }
    };

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.on('line', () => {
      rl.close();
      finish();
    });

    if (process.stdin.isTTY) {
      process.stdin.setRawMode?.(true);
      process.stdin.resume();
      process.stdin.on('data', (buf) => {
        const str = buf.toString();
        // Enter (CR or LF) or Ctrl+C
        if (str.includes('\r') || str.includes('\n') || str.includes('\u0003')) {
          process.stdin.setRawMode?.(false);
          finish();
        }
      });
    }
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
