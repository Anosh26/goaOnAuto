/**
 * GoaOnAuto Residence Certificate Automation Runner.
 * Single Responsibility: Resolves the target applicant directory and launches the Raylib Residence Certificate GUI.
 */
import * as path from 'path';
import * as fs from 'fs';
import { spawn } from 'child_process';
import { config } from '../config';

function findLatestApplicantDir(rootWorkDir: string): string | null {
  if (!fs.existsSync(rootWorkDir)) return null;

  const candidates: { path: string; mtime: number }[] = [];

  function scanDir(dir: string, depth = 0) {
    if (depth > 3) return;
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      let hasDossierOrJpg = false;

      for (const entry of entries) {
        if (entry.name === 'applicant_dossier.json' || entry.name.endsWith('.jpg') || entry.name.endsWith('.png')) {
          hasDossierOrJpg = true;
        }
      }

      if (hasDossierOrJpg) {
        const stat = fs.statSync(dir);
        candidates.push({ path: dir, mtime: stat.mtimeMs });
      }

      for (const entry of entries) {
        if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
          scanDir(path.join(dir, entry.name), depth + 1);
        }
      }
    } catch {
      // Ignore read permission errors
    }
  }

  scanDir(rootWorkDir);

  if (candidates.length === 0) return null;
  candidates.sort((a, b) => b.mtime - a.mtime);
  return candidates[0]?.path ?? null;
}

export function launchResidenceGui(targetDir?: string): void {
  let selectedDir = targetDir;

  if (!selectedDir) {
    // Check CLI argument
    const args = process.argv.slice(2);
    const dirFlagIndex = args.indexOf('--dir');
    if (dirFlagIndex !== -1 && args[dirFlagIndex + 1]) {
      selectedDir = args[dirFlagIndex + 1];
    } else if (args[0] && !args[0].startsWith('--')) {
      selectedDir = args[0];
    }
  }

  if (!selectedDir) {
    // Look for latest folder with dossier or images
    selectedDir = findLatestApplicantDir(config.workDir) || path.join(config.projectRoot, 'scratch');
  }

  const resolvedDir = path.resolve(selectedDir);
  console.log(`===================================================`);
  console.log(`🏛️  GoaOnAuto Residence Certificate Automation`);
  console.log(`📂 Target Applicant Directory: ${resolvedDir}`);
  console.log(`🎨 Launching Raylib Dynamic Scalable GUI...`);
  console.log(`===================================================\n`);

  const pythonScript = path.join(config.projectRoot, 'python', 'gui', 'residence_gui.py');
  const pythonBin = config.pythonBin || 'python';

  const child = spawn(pythonBin, [pythonScript, '--dir', resolvedDir], {
    stdio: 'inherit',
    cwd: config.projectRoot,
    shell: false
  });

  child.on('error', (err) => {
    console.error(`❌ Failed to launch Residence GUI: ${err.message}`);
  });

  child.on('exit', (code) => {
    if (code === 0) {
      console.log(`\n✅ Residence Certificate Automation GUI closed successfully.`);
    } else {
      console.log(`\nℹ️  Residence Certificate GUI exited with code ${code}.`);
    }
  });
}

// Direct CLI execution
if (import.meta.main || require.main === module) {
  launchResidenceGui();
}
