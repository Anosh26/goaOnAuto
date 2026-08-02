import { execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

const pythonScript = path.resolve(__dirname, 'imageOps.py');

/**
 * Merge front side (top) and back side (bottom) of an ID card vertically
 */
export function mergeCardFrontBackVertically(frontPath: string, backPath: string, outputPath: string): string {
  const cmd = `python "${pythonScript}" merge_vertical "${frontPath}" "${backPath}" "${outputPath}"`;
  execSync(cmd, { stdio: 'pipe' });
  return outputPath;
}

/**
 * Convert multiple sequential images into a single multi-page PDF document
 */
export function convertImagesToMultipagePdf(imagePaths: string[], outputPdfPath: string): string {
  const formattedPaths = imagePaths.map(p => `"${p}"`).join(' ');
  const cmd = `python "${pythonScript}" convert_to_pdf "${outputPdfPath}" ${formattedPaths}`;
  execSync(cmd, { stdio: 'pipe' });
  return outputPdfPath;
}
