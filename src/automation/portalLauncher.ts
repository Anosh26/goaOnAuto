/**
 * GoaOnAuto Portal Browser Launcher.
 * Single Responsibility: Launches Brave Browser in headed mode with isolated profile
 * and Playwright automation hooks.
 */
import * as path from 'path';
import * as fs from 'fs';
import { chromium, BrowserContext, Page, LaunchOptions } from '@playwright/test';
import { config } from '../config';

export interface BraveLaunchOptions {
  headless?: boolean;
  userDataDir?: string;
  persistent?: boolean;
  bravePath?: string;
}

const DEFAULT_BRAVE_PATHS = [
  process.env.BRAVE_BIN,
  'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
  'C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
  path.join(process.env.LOCALAPPDATA || '', 'BraveSoftware\\Brave-Browser\\Application\\brave.exe'),
].filter((p): p is string => Boolean(p && fs.existsSync(p)));

/**
 * Resolves the path to the Brave Browser executable.
 */
export function getBraveExecutablePath(customPath?: string): string {
  if (customPath && fs.existsSync(customPath)) {
    return customPath;
  }
  if (DEFAULT_BRAVE_PATHS.length > 0 && DEFAULT_BRAVE_PATHS[0]) {
    return DEFAULT_BRAVE_PATHS[0];
  }
  throw new Error(
    'Brave Browser executable not found. Please ensure Brave is installed at ' +
    'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe or set BRAVE_BIN in .env'
  );
}

export interface LaunchedPortalSession {
  context: BrowserContext;
  page: Page;
  close: () => Promise<void>;
}

/**
 * Cleans up stale lock files from previous runs to prevent Chrome profile lock crashes.
 */
function cleanupStaleLockFiles(profileDir: string): void {
  try {
    const lockFile = path.join(profileDir, 'SingletonLock');
    if (fs.existsSync(lockFile)) {
      fs.unlinkSync(lockFile);
    }
    const cookieLock = path.join(profileDir, 'lockfile');
    if (fs.existsSync(cookieLock)) {
      fs.unlinkSync(cookieLock);
    }
  } catch {
    // Ignore cleanup error if file is currently held
  }
}

/**
 * Launches Brave browser for GoaOnline automation.
 * By default launches with a persistent context in `.brave_automation_profile` so that
 * user preferences / sessions can be maintained cleanly without affecting personal Brave sessions.
 */
export async function launchBrave(options: BraveLaunchOptions = {}): Promise<LaunchedPortalSession> {
  const braveBin = getBraveExecutablePath(options.bravePath);
  const profileDir = options.userDataDir || path.join(config.projectRoot, '.brave_automation_profile');

  if (!fs.existsSync(profileDir)) {
    fs.mkdirSync(profileDir, { recursive: true });
  }

  cleanupStaleLockFiles(profileDir);

  const headless = options.headless ?? false;
  const commonArgs = [
    '--start-maximized',
    '--disable-blink-features=AutomationControlled',
    '--no-default-browser-check',
    '--no-first-run'
  ];

  console.log(`🚀 Launching Brave Browser: ${braveBin}`);
  console.log(`📁 Profile directory: ${profileDir}`);

  let context: BrowserContext;

  try {
    context = await chromium.launchPersistentContext(profileDir, {
      executablePath: braveBin,
      headless,
      viewport: null, // Let Brave use the maximized window dimensions
      args: commonArgs,
      ignoreDefaultArgs: ['--enable-automation']
    });
  } catch (err: any) {
    console.warn(`⚠️  Persistent context launch failed (${err.message}). Retrying with fresh browser instance...`);
    const browser = await chromium.launch({
      executablePath: braveBin,
      headless,
      args: commonArgs,
      ignoreDefaultArgs: ['--enable-automation']
    });
    context = await browser.newContext({
      viewport: null
    });
  }

  // Get the first open page or create a new one
  const page = context.pages()[0] ?? (await context.newPage());

  return {
    context,
    page,
    close: async () => {
      try {
        await context.close();
      } catch {
        // Ignore close error
      }
    }
  };
}
