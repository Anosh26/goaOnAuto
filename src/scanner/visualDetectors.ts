/**
 * Visual Feature CLI Fallback Detectors.
 * Single Responsibility: Invokes Python photo and signature visual feature scripts via CLI when daemon is unavailable.
 */
import * as path from 'path';
import { execSync } from 'child_process';
import { config } from '../config';

export function tryPassportPhotoDetector(imagePath: string): { isPassport: boolean; confidence: number; reason?: string } {
  const pyScript = path.join(config.pythonDir, 'vision', 'photo_detector.py');
  try {
    const output = execSync(`"${config.pythonBin}" "${pyScript}" "${imagePath}"`, { 
      cwd: config.projectRoot,
      stdio: 'pipe' 
    }).toString();
    const parsed = JSON.parse(output);
    if (parsed && parsed.is_passport_photo) {
      return {
        isPassport: true,
        confidence: parsed.confidence || 0.9,
        reason: parsed.reason,
      };
    }
  } catch {}
  return { isPassport: false, confidence: 0 };
}

export function trySignatureDetector(imagePath: string): { isSignature: boolean; confidence: number; inkType?: string; reason?: string } {
  const pyScript = path.join(config.pythonDir, 'vision', 'signature_detector.py');
  try {
    const output = execSync(`"${config.pythonBin}" "${pyScript}" "${imagePath}"`, { 
      cwd: config.projectRoot,
      stdio: 'pipe' 
    }).toString();
    const parsed = JSON.parse(output);
    if (parsed && parsed.is_signature) {
      return {
        isSignature: true,
        confidence: parsed.confidence || 0.85,
        inkType: parsed.ink_type,
        reason: parsed.reason,
      };
    }
  } catch {}
  return { isSignature: false, confidence: 0 };
}
