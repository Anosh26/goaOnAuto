import { Page, BrowserContext } from '@playwright/test';
import { startPortalPhase1, PortalSessionConfig } from '../../src/automation/services/portalSessionManager';
import { attachVisualTracker } from '../../src/automation/utils/visualTracker';

export interface TestSession {
  context: BrowserContext;
  page: Page;
  currentUrl: string;
}

export async function setupTestSession(sessionName: string, config: PortalSessionConfig = {}): Promise<TestSession> {
  console.log(`\n🤖 [TestRunner] Initializing session: ${sessionName}`);
  const session = await startPortalPhase1(config);
  
  // Attach the visual tracker so the bot's actions are recorded and highlighted
  await attachVisualTracker(session.context, sessionName);
  
  return session;
}

export async function teardownTestSession(session: TestSession) {
  console.log('\n🔒 [TestRunner] Closing browser session...');
  await session.context.close().catch(() => {});
}
