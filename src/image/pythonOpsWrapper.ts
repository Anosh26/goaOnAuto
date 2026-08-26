/**
 * Python Vision Image Operations Wrapper.
 * Single Responsibility: Invokes Python utilities for vertical card merging and multipage PDF conversion.
 */
import { execSync } from 'child_process';
import * as path from 'path';
import { config } from '../config';

/**
 * Merge front side (top) and back side (bottom) of an ID card vertically
 */
export function mergeCardFrontBackVertically(frontPath: string, backPath: string, outputPath: string): string {
  const scriptPath = path.join(config.pythonDir, 'utils', 'card_merger.py');
  const cmd = `"${config.pythonBin}" "${scriptPath}" "${frontPath}" "${backPath}" "${outputPath}"`;
  execSync(cmd, { cwd: config.projectRoot, stdio: 'pipe' });
  return outputPath;
}

/**
 * Convert multiple sequential images into a single multi-page PDF document
 */
export function convertImagesToMultipagePdf(imagePaths: string[], outputPdfPath: string): string {
  const scriptPath = path.join(config.pythonDir, 'utils', 'pdf_converter.py');
  const formattedPaths = imagePaths.map(p => `"${p}"`).join(' ');
  const cmd = `"${config.pythonBin}" "${scriptPath}" "${outputPdfPath}" ${formattedPaths}`;
  execSync(cmd, { cwd: config.projectRoot, stdio: 'pipe' });
  return outputPdfPath;
}
