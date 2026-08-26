/**
 * Captcha Recognition Solver.
 * Single Responsibility: Recognizes single-line alphanumeric captcha image buffers using Tesseract.
 */
import { createWorker, PSM } from 'tesseract.js';

export async function solveCaptcha(imageBuffer: Buffer): Promise<string> {
  const worker = await createWorker('eng');

  await worker.setParameters({
    tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    tessedit_pageseg_mode: PSM.SINGLE_LINE,
  });

  const { data: { text } } = await worker.recognize(imageBuffer);
  await worker.terminate();
  return text.replace(/\s/g, '').trim();
}
