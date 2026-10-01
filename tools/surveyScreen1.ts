/**
 * GoaOnAuto - Screen 1 Survey & Human Simulation Tracker.
 * Single Responsibility:
 * 1. Launches Brave and automatically navigates through REV05 -> Proceed to Apply -> Screen 1.
 * 2. Surveys and categorizes every interactive element on Screen 1 (inputs, radios, dropdowns, uploads).
 * 3. Injects live action tracker so the user can interactively fill the form by hand.
 * 4. Captures real-time Playwright-ready selectors, values, and blueprints to recordings/.
 */
import * as path from 'path';
import * as fs from 'fs';
import * as readline from 'readline';
import { Page } from '@playwright/test';
import { startPortalPhase1, updatePortalStatusOverlay } from '../src/automation/services/portalSessionManager';

export interface FieldSurveyItem {
  index: number;
  label: string;
  tag: string;
  type: string;
  id: string;
  name: string;
  value: string;
  placeholder: string;
  options?: { value: string; text: string }[];
  suggestedSelector: string;
}

export interface RecordedSimulationAction {
  index: number;
  timestamp: string;
  eventType: 'click' | 'change' | 'input' | 'navigation';
  pageUrl: string;
  tag: string;
  id: string;
  name: string;
  inputType?: string;
  label: string;
  value: string;
  selectedText?: string;
  suggestedSelector: string;
  suggestedPlaywrightCode: string;
}

const RECORDINGS_DIR = path.join(process.cwd(), 'recordings');
if (!fs.existsSync(RECORDINGS_DIR)) {
  fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
}

async function surveyPageDom(page: Page): Promise<FieldSurveyItem[]> {
  const surveyScript = `(() => {
    function findLabel(el) {
      if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
      if (el.getAttribute('placeholder')) return el.getAttribute('placeholder');
      if (el.getAttribute('title')) return el.getAttribute('title');

      if (el.id) {
        const labelEl = document.querySelector('label[for="' + el.id + '"]');
        if (labelEl && labelEl.textContent) return labelEl.textContent.trim();
      }

      const parentLabel = el.closest('label');
      if (parentLabel && parentLabel.textContent) return parentLabel.textContent.trim();

      const td = el.closest('td');
      if (td && td.previousElementSibling && td.previousElementSibling.textContent) {
        const txt = td.previousElementSibling.textContent.replace(/[*:]/g, '').trim();
        if (txt) return txt;
      }

      const parentRow = el.closest('.form-group, .row, p, tr, div');
      if (parentRow) {
        const label = parentRow.querySelector('label, .control-label, span.label, th');
        if (label && label.textContent && label.textContent.trim()) {
          return label.textContent.replace(/[*:]/g, '').trim();
        }
      }

      return el.getAttribute('name') || el.id || el.tagName.toLowerCase();
    }

    const elements = Array.from(document.querySelectorAll('input, select, textarea, button'));
    const items = [];
    let idx = 0;

    for (const raw of elements) {
      const el = raw;
      const tag = el.tagName.toLowerCase();
      const type = el.type || '';

      // Skip hidden inputs unless relevant
      if (type === 'hidden') continue;

      idx++;
      const id = el.id || '';
      const name = el.getAttribute('name') || '';
      const label = findLabel(el);
      const value = el.value || '';
      const placeholder = el.placeholder || '';

      let options = undefined;
      if (tag === 'select') {
        options = Array.from(el.options).map(o => ({ value: o.value, text: (o.text || '').trim() }));
      }

      let selector = '';
      if (id) selector = '#' + id;
      else if (name) selector = '[name="' + name + '"]';
      else if (label && label.length < 30) selector = tag + ':has-text("' + label + '")';
      else selector = tag;

      items.push({
        index: idx,
        label,
        tag,
        type,
        id,
        name,
        value,
        placeholder,
        options,
        suggestedSelector: selector
      });
    }

    return items;
  })()`;

  return await page.evaluate(surveyScript);
}

async function main() {
  console.log('========================================================================');
  console.log('🔍 GOAONAUTO - SCREEN 1 SURVEY & INTERACTIVE SIMULATION TRACKER');
  console.log('🎯 Scope: Launch Brave -> Screen 1 -> Survey DOM -> Live Hand Simulation');
  console.log('========================================================================\n');

  const keepSession = process.argv.includes('--keep-session') || true;
  const sessionTimestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const surveyJsonPath = path.join(RECORDINGS_DIR, `screen1_survey_${sessionTimestamp}.json`);
  const surveyMdPath = path.join(RECORDINGS_DIR, 'screen1_survey_latest.md');
  const simulationJsonPath = path.join(RECORDINGS_DIR, `screen1_simulation_${sessionTimestamp}.json`);
  const simulationMdPath = path.join(RECORDINGS_DIR, 'screen1_simulation_latest.md');

  // Step 1: Launch and navigate directly to Screen 1
  console.log('🚀 Connecting to Brave and navigating to Residence Form Screen 1...');
  const session = await startPortalPhase1({
    freshLogin: !keepSession,
    loginTimeoutMs: 300000
  });

  const formPage = session.page;
  await formPage.bringToFront();
  await updatePortalStatusOverlay(formPage, '🔍 GoaOnAuto: Running Screen 1 DOM Survey...', 'working');

  // Step 2: Survey DOM fields
  console.log('\n📊 Surveying interactive controls on Screen 1...');
  const fields = await surveyPageDom(formPage);

  console.log(`\n📋 Found ${fields.length} interactive form controls on Screen 1:\n`);
  console.log('| # | Type / Tag | Label | ID / Name | Options / Value |');
  console.log('|---|---|---|---|---|');
  fields.forEach(f => {
    const typeTag = f.type ? `${f.tag}[${f.type}]` : f.tag;
    const idName = f.id ? `#${f.id}` : (f.name ? `name="${f.name}"` : '-');
    const extra = f.options && f.options.length > 0 
      ? `(${f.options.length} options: ${f.options.slice(0, 3).map(o => o.text).join(', ')}...)`
      : (f.value ? `val: "${f.value}"` : (f.placeholder ? `ph: "${f.placeholder}"` : '-'));
    console.log(`| ${f.index} | \`${typeTag}\` | **${f.label}** | \`${idName}\` | ${extra} |`);
  });

  // Save survey markdown
  let surveyMd = `# GoaOnline Residence Certificate - Screen 1 DOM Survey\n\n`;
  surveyMd += `*Inspected ${fields.length} interactive controls on ${new Date().toLocaleString()}*\n`;
  surveyMd += `*Page URL: ${formPage.url()}*\n\n`;
  surveyMd += `| # | Type / Tag | Field Label | Selector | Values / Options |\n`;
  surveyMd += `|---|---|---|---|---|\n`;
  for (const f of fields) {
    const typeTag = f.type ? `${f.tag}[type="${f.type}"]` : f.tag;
    const opts = f.options ? f.options.map(o => `"${o.text}" (${o.value})`).join(', ') : (f.value || '-');
    surveyMd += `| ${f.index} | \`${typeTag}\` | **${f.label}** | \`${f.suggestedSelector}\` | ${opts} |\n`;
  }
  fs.writeFileSync(surveyJsonPath, JSON.stringify(fields, null, 2), 'utf-8');
  fs.writeFileSync(surveyMdPath, surveyMd, 'utf-8');
  console.log(`\n💾 Survey results saved to: ${surveyMdPath}`);

  // Step 3: Inject Live Simulation Tracker
  const recordedActions: RecordedSimulationAction[] = [];
  let actionCounter = 0;

  await session.context.exposeFunction('__goaOnAutoRecordSimulation', async (raw: any) => {
    actionCounter++;
    const action: RecordedSimulationAction = {
      index: actionCounter,
      timestamp: new Date().toLocaleTimeString(),
      eventType: raw.eventType,
      pageUrl: raw.pageUrl || formPage.url(),
      tag: raw.tag || '',
      id: raw.id || '',
      name: raw.name || '',
      inputType: raw.inputType || '',
      label: raw.label || 'Unlabeled',
      value: raw.value || '',
      selectedText: raw.selectedText || '',
      suggestedSelector: raw.suggestedSelector || '',
      suggestedPlaywrightCode: raw.suggestedPlaywrightCode || ''
    };

    recordedActions.push(action);
    fs.writeFileSync(simulationJsonPath, JSON.stringify(recordedActions, null, 2), 'utf-8');
    generateSimulationMarkdown(recordedActions, simulationMdPath);

    const icon = action.eventType === 'click' ? '🖱️' : action.eventType === 'change' ? '🔽' : '📝';
    console.log(`\n[#${String(action.index).padStart(2, '0')}] ${icon} ${action.eventType.toUpperCase()} | "${action.label}"`);
    console.log(`      Tag: <${action.tag}${action.inputType ? ` type="${action.inputType}"` : ''}> | Selector: \`${action.suggestedSelector}\``);
    if (action.selectedText) console.log(`      Selected: "${action.selectedText}" (val: "${action.value}")`);
    else if (action.value) console.log(`      Value: "${action.value}"`);
    console.log(`      💻 Playwright: ${action.suggestedPlaywrightCode}`);

    await updatePortalStatusOverlay(formPage, `🔴 Captured: #${action.index} (${action.label.substring(0, 20)})`, 'working');
  });

  const injectScript = `(() => {
    if (window.__goaOnAutoSimInjected) return;
    window.__goaOnAutoSimInjected = true;

    function findLabel(el) {
      if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
      if (el.getAttribute('placeholder')) return el.getAttribute('placeholder');
      if (el.getAttribute('title')) return el.getAttribute('title');

      if (el.id) {
        const labelEl = document.querySelector('label[for="' + el.id + '"]');
        if (labelEl && labelEl.textContent) return labelEl.textContent.trim();
      }

      const parentLabel = el.closest('label');
      if (parentLabel && parentLabel.textContent) return parentLabel.textContent.trim();

      const td = el.closest('td');
      if (td && td.previousElementSibling && td.previousElementSibling.textContent) {
        const txt = td.previousElementSibling.textContent.replace(/[*:]/g, '').trim();
        if (txt) return txt;
      }

      const parentRow = el.closest('.form-group, .row, p, tr, div');
      if (parentRow) {
        const label = parentRow.querySelector('label, .control-label, span.label, th');
        if (label && label.textContent && label.textContent.trim()) {
          return label.textContent.replace(/[*:]/g, '').trim();
        }
      }

      return el.getAttribute('name') || el.id || el.tagName.toLowerCase();
    }

    function highlight(el) {
      const origOutline = el.style.outline;
      const origBoxShadow = el.style.boxShadow;
      el.style.outline = '3px solid #50fa7b';
      el.style.boxShadow = '0 0 12px #50fa7b';
      setTimeout(() => {
        el.style.outline = origOutline;
        el.style.boxShadow = origBoxShadow;
      }, 700);
    }

    function makeSelector(el) {
      if (el.id) return '#' + el.id;
      const name = el.getAttribute('name');
      if (name) return '[name="' + name + '"]';
      const label = findLabel(el);
      if (label && label.length < 30) return el.tagName.toLowerCase() + ':has-text("' + label + '")';
      return el.tagName.toLowerCase();
    }

    // CLICKS
    window.addEventListener('click', (e) => {
      const target = e.target.closest('a, button, input[type="radio"], input[type="checkbox"], [role="button"]') || e.target;
      if (!target || target.id === 'goaonauto-status-pill') return;

      highlight(target);
      const tag = target.tagName.toLowerCase();
      const type = target.type || '';
      const label = findLabel(target);
      const val = target.value || target.textContent?.trim() || '';
      const selector = makeSelector(target);

      let code = '';
      if (type === 'radio' || type === 'checkbox') {
        code = "await page.check('" + selector + "');";
      } else {
        code = "await page.locator('" + selector + "').click();";
      }

      if (window.__goaOnAutoRecordSimulation) {
        window.__goaOnAutoRecordSimulation({
          eventType: 'click',
          tag,
          id: target.id || '',
          name: target.getAttribute('name') || '',
          inputType: type,
          label,
          value: val,
          suggestedSelector: selector,
          suggestedPlaywrightCode: code
        });
      }
    }, true);

    // DROPDOWNS & FILE UPLOADS
    window.addEventListener('change', (e) => {
      const target = e.target;
      if (!target) return;
      const tag = target.tagName.toLowerCase();
      const type = target.type || '';
      const label = findLabel(target);
      const selector = makeSelector(target);

      if (tag === 'select') {
        const opt = target.selectedOptions ? target.selectedOptions[0] : null;
        const val = target.value;
        const text = opt ? opt.text.trim() : '';
        const code = "await page.selectOption('" + selector + "', { label: '" + text + "' });";

        if (window.__goaOnAutoRecordSimulation) {
          window.__goaOnAutoRecordSimulation({
            eventType: 'change',
            tag,
            id: target.id || '',
            name: target.getAttribute('name') || '',
            inputType: type,
            label,
            value: val,
            selectedText: text,
            suggestedSelector: selector,
            suggestedPlaywrightCode: code
          });
        }
      } else if (type === 'file') {
        const fileName = target.files && target.files[0] ? target.files[0].name : '';
        const code = "await page.setInputFiles('" + selector + "', 'path/to/" + (fileName || 'document.pdf') + "');";

        if (window.__goaOnAutoRecordSimulation) {
          window.__goaOnAutoRecordSimulation({
            eventType: 'change',
            tag,
            id: target.id || '',
            name: target.getAttribute('name') || '',
            inputType: type,
            label,
            value: fileName,
            suggestedSelector: selector,
            suggestedPlaywrightCode: code
          });
        }
      }
    }, true);

    // INPUT & BLUR
    let timer = null;
    window.addEventListener('input', (e) => {
      const target = e.target;
      if (!target || target.tagName.toLowerCase() === 'select') return;
      clearTimeout(timer);
      timer = setTimeout(() => {
        const label = findLabel(target);
        const val = target.value;
        const selector = makeSelector(target);
        const code = "await page.fill('" + selector + "', '" + val + "');";

        if (window.__goaOnAutoRecordSimulation) {
          window.__goaOnAutoRecordSimulation({
            eventType: 'input',
            tag: target.tagName.toLowerCase(),
            id: target.id || '',
            name: target.getAttribute('name') || '',
            inputType: target.type || '',
            label,
            value: val,
            suggestedSelector: selector,
            suggestedPlaywrightCode: code
          });
        }
      }, 600);
    }, true);
  })();`;

  await formPage.evaluate(injectScript).catch(() => {});
  await session.context.addInitScript(injectScript);

  await updatePortalStatusOverlay(formPage, '🟢 Simulation Ready: Fill form naturally in Brave', 'success');

  console.log('\n========================================================================');
  console.log('🟢 LIVE SURVEY & TRACKER IS RUNNING IN BRAVE!');
  console.log('👉 Go to your open Brave window on Screen 1.');
  console.log('👉 Fill out the form by hand (select Self/Relative, Purpose, Name, Address, etc.).');
  console.log('👉 Each action will be tracked and printed here live.');
  console.log('👉 When you have finished simulating Screen 1, press [ENTER] in this terminal.');
  console.log('========================================================================\n');

  // Wait for user to finish simulation via ENTER
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  await new Promise<void>((resolve) => {
    rl.question('', () => {
      rl.close();
      resolve();
    });
  });

  console.log('\n========================================================================');
  console.log(`🎉 SIMULATION RECORDED! Captured ${recordedActions.length} user actions.`);
  console.log(`💾 Blueprint saved to: ${simulationMdPath}`);
  console.log('========================================================================\n');

  await session.context.close().catch(() => {});
  process.exit(0);
}

function generateSimulationMarkdown(actions: RecordedSimulationAction[], outputPath: string): void {
  let md = '# Screen 1 Human Simulation Blueprint\n\n';
  md += `*Captured ${actions.length} user actions on ${new Date().toLocaleString()}*\n\n`;
  md += '## Playwright Code\n\n```typescript\n';
  for (const a of actions) {
    md += `// [Step ${a.index}] ${a.label} (${a.eventType})\n`;
    md += `${a.suggestedPlaywrightCode}\n`;
  }
  md += '```\n\n';
  md += '## Action Log\n\n';
  md += '| # | Action | Field Label | Control ID | Value / Text |\n';
  md += '|---|---|---|---|---|\n';
  for (const a of actions) {
    const val = a.selectedText || a.value || '-';
    md += `| ${a.index} | **${a.eventType.toUpperCase()}** | ${a.label} | \`${a.id || a.name || '-'}\` | \`${val.substring(0, 40)}\` |\n`;
  }
  fs.writeFileSync(outputPath, md, 'utf-8');
}

main().catch((err) => {
  console.error('❌ Survey Tracker error:', err);
  process.exit(1);
});
