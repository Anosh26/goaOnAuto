/**
 * Native C Image Processor Binding.
 * Single Responsibility: Executes the compiled C binary (process_image.exe) for fast downscaling & JPEG compression.
 */
import * as fs from 'fs';
import { spawnSync } from 'child_process';
import { config } from '../config';

export interface NativeCompressOptions {
  maxKB?: number;
  width?: number;
  height?: number;
  skipBgRemove?: boolean;
}

export function compressImageWithNativeEngine(
  inputPath: string,
  outputPath: string,
  options: NativeCompressOptions = {}
): string {
  const exePath = config.imageProcessorExe;
  if (!fs.existsSync(exePath)) {
    throw new Error(`Native image processor binary not found at: ${exePath}`);
  }

  const args: string[] = [];
  if (options.maxKB) {
    args.push('--max-kb', options.maxKB.toString());
  }
  if (options.skipBgRemove) {
    args.push('--skip-bg-remove');
  }
  if (options.width) {
    args.push('--width', options.width.toString());
  }
  if (options.height) {
    args.push('--height', options.height.toString());
  }

  args.push(`"${inputPath}"`, `"${outputPath}"`);

  const result = spawnSync(`"${exePath}"`, args, { shell: true, encoding: 'utf-8' });

  if (result.status !== 0 || !fs.existsSync(outputPath)) {
    throw new Error(`C Image Processor execution failed: ${result.stderr || result.stdout}`);
  }

  return outputPath;
}
