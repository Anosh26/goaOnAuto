/**
 * Centralized Configuration & Environment Path Resolver.
 * Single Responsibility: Loads .env variables and exports strongly-typed system paths.
 */
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

export interface AppConfig {
  projectRoot: string;
  workDir: string;
  stagingDir: string;
  binDir: string;
  modelsDir: string;
  pythonDir: string;
  pythonBin: string;
  imageProcessorExe: string;
  yunetModelPath: string;
  // Resource Limits & Throttling
  minFreeRamBytes: number; // Keep at least 3 GB free system RAM for other laptop processes
  maxCpuPercent: number;    // Keep at least 20% free CPU (max 80% total utilization)
  maxGpuMemoryFraction: number; // Cap GPU usage at 90% max
  enableHumanConfirmation: boolean; // Raylib GUI confirmation popup toggle
}

function loadEnvFile(envPath: string): void {
  if (fs.existsSync(envPath)) {
    const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const [key, ...valParts] = trimmed.split('=');
      if (key && valParts.length > 0) {
        const val = valParts.join('=').trim().replace(/^["']|["']$/g, '');
        const trimmedKey = key.trim();
        if (!process.env[trimmedKey]) {
          process.env[trimmedKey] = val;
        }
      }
    }
  }
}

const PROJECT_ROOT = path.resolve(__dirname, '../../');
loadEnvFile(path.join(PROJECT_ROOT, '.env'));

function resolvePythonBinary(): string {
  // 1. Explicit env var override (highest priority — use when venv lacks packages like raylib)
  if (process.env.PYTHON_BIN && fs.existsSync(process.env.PYTHON_BIN)) return process.env.PYTHON_BIN;

  // 2. Virtual environment python if present (Scripts/ for standard Windows, bin/ for MSYS2/uv)
  const venvPythonScripts = path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe');
  if (fs.existsSync(venvPythonScripts)) return venvPythonScripts;

  const venvPythonBin = path.join(PROJECT_ROOT, '.venv', 'bin', 'python.exe');
  if (fs.existsSync(venvPythonBin)) return venvPythonBin;

  const venvPosix = path.join(PROJECT_ROOT, '.venv', 'bin', 'python');
  if (fs.existsSync(venvPosix)) return venvPosix;

  // 3. Default system python
  return process.platform === 'win32' ? 'python' : 'python3';
}

const WORK_DIR = process.env.DOCUMENT_WATCH_PATH || 
                 process.env.WORK_DIR_PATH || 
                 path.resolve(PROJECT_ROOT, 'work_directory');

const STAGING_DIR = path.join(os.tmpdir(), 'goaOnAuto_drive_stage');
const BIN_DIR = path.join(PROJECT_ROOT, 'bin');
const ASSETS_DIR = path.join(PROJECT_ROOT, 'assets');
const MODELS_DIR = path.join(ASSETS_DIR, 'models');
const PYTHON_DIR = path.join(PROJECT_ROOT, 'python');

export const config: AppConfig = {
  projectRoot: PROJECT_ROOT,
  workDir: WORK_DIR,
  stagingDir: STAGING_DIR,
  binDir: BIN_DIR,
  modelsDir: MODELS_DIR,
  pythonDir: PYTHON_DIR,
  pythonBin: resolvePythonBinary(),
  imageProcessorExe: path.join(BIN_DIR, 'process_image.exe'),
  yunetModelPath: path.join(MODELS_DIR, 'face_detection_yunet_2023mar.onnx'),
  minFreeRamBytes: parseFloat(process.env.MIN_FREE_RAM_GB || '3.0') * 1024 * 1024 * 1024,
  maxCpuPercent: parseFloat(process.env.MAX_CPU_PERCENT || '80.0'),
  maxGpuMemoryFraction: parseFloat(process.env.MAX_GPU_MEMORY_FRACTION || '0.90'),
  enableHumanConfirmation: process.env.ENABLE_HUMAN_CONFIRMATION !== 'false'
};

