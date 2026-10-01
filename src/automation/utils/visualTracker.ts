import { Page, BrowserContext } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

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

export const injectTrackerScript = `(() => {
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

  ensureStatusPill('🤖 GoaOnAuto Automation Running');

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
    el.style.outline = '3px solid #ff79c6';
    el.style.boxShadow = '0 0 12px #ff79c6';
    setTimeout(() => {
      el.style.outline = origOutline;
      el.style.boxShadow = origBoxShadow;
    }, 700);
  }

  // Bind to clicks
  window.addEventListener('click', (e) => {
    const target = e.target.closest('a, button, input, select, textarea, [role="button"]') || e.target;
    if (!target || target.id === 'goaonauto-status-pill') return;

    // We don't auto-highlight here in automated mode because the automation script will do it
    // But we still track manual clicks if they happen during automated testing
    if (!e.isTrusted && !window.__goaOnAutoHighlightEnabled) return; // ignore synthetic clicks unless highlight is enabled

    if (window.__goaOnAutoHighlightEnabled) highlightElement(target);

    const postBack = getPostBackInfo(target);
    const tag = target.tagName.toLowerCase();
    const label = findLabelFor(target);
    const textVal = target.textContent?.trim() || target.value || '';
    const { selector, code } = generateSelectorAndCode(target, 'click', textVal);

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

  // Expose highlight function for Playwright script to call explicitly
  window.__goaOnAutoHighlightElementBySelector = (selector) => {
    const el = document.querySelector(selector);
    if (el) {
      highlightElement(el);
      ensureStatusPill('🤖 Bot action: ' + selector);
    }
  };

})();`;

export async function attachVisualTracker(context: BrowserContext, sessionName: string) {
  const RECORDINGS_DIR = path.join(process.cwd(), 'recordings');
  if (!fs.existsSync(RECORDINGS_DIR)) {
    fs.mkdirSync(RECORDINGS_DIR, { recursive: true });
  }

  const sessionTimestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const jsonTracePath = path.join(RECORDINGS_DIR, `bot_trace_${sessionName}_${sessionTimestamp}.json`);
  const recordedActions: RecordedAction[] = [];
  let actionCounter = 0;

  await context.exposeFunction('__goaOnAutoRecordAction', async (rawAction: any) => {
    actionCounter++;
    const action: RecordedAction = {
      index: actionCounter,
      timestamp: new Date().toLocaleTimeString(),
      eventType: rawAction.eventType,
      pageUrl: rawAction.pageUrl || '',
      pageTitle: rawAction.pageTitle || '',
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
    fs.writeFileSync(jsonTracePath, JSON.stringify(recordedActions, null, 2), 'utf-8');
    
    console.log(`\n[BOT TRACKER] #${action.index} ${action.eventType.toUpperCase()} | ${action.label} | Selector: ${action.suggestedSelector}`);
  });

  await context.addInitScript(injectTrackerScript);

  const attachToPage = async (p: Page) => {
    try {
      await p.evaluate(injectTrackerScript).catch(() => {});
    } catch {}

    p.on('domcontentloaded', async () => {
      await p.evaluate(injectTrackerScript).catch(() => {});
    });
  };

  for (const p of context.pages()) {
    await attachToPage(p);
  }

  context.on('page', async (newPage) => {
    await attachToPage(newPage);
  });
}
