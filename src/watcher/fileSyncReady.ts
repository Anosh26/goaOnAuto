/**
 * File Sync Stability & Safe Unlink Module.
 * Single Responsibility: Detects Google Drive file sync completion and executes lock-safe file removal.
 */
import * as fs from 'fs';
import * as path from 'path';

/**
 * Waits until Google Drive or file write operations finish syncing to disk (file size is stable).
 */
export async function waitForFileReady(filePath: string, maxWaitMs = 5000): Promise<boolean> {
  const start = Date.now();
  let lastSize = -1;

  while (Date.now() - start < maxWaitMs) {
    try {
      if (!fs.existsSync(filePath)) return false;
      const stats = fs.statSync(filePath);
      if (!stats.isFile()) return false;

      if (stats.size > 0 && stats.size === lastSize) {
        return true;
      }
      lastSize = stats.size;
    } catch {}
    await new Promise(r => setTimeout(r, 300));
  }
  return fs.existsSync(filePath) && fs.statSync(filePath).isFile();
}

/**
 * Retries unlinking files to safely overcome temporary Google Drive / Windows file locks.
 */
export function safeUnlink(filePath: string, retries = 5): void {
  for (let i = 0; i < retries; i++) {
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
      return;
    } catch (e) {
      if (i === retries - 1) {
        console.warn(`⚠️ Could not remove original file (Locked): ${path.basename(filePath)}`);
      }
      const end = Date.now() + 200;
      while (Date.now() < end) {}
    }
  }
}
