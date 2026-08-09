import { describe, test, expect, beforeAll, afterAll } from 'bun:test';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';
import { tryPassportPhotoDetector, processDocumentImage } from '../utils/documentScanner';
import { classifyDocumentText } from '../utils/documentClassifier';
import { processPhotoForUpload } from '../utils/imageProcessor';

const testDir = path.resolve('./tests/mock_photo_test');
const mockPassportImg = path.join(testDir, 'sample_passport_photo.jpg');
const mockDocImg = path.join(testDir, 'sample_doc_no_face.jpg');

describe('Passport Size Photo Detector & White BG Generator', () => {
  beforeAll(() => {
    fs.mkdirSync(testDir, { recursive: true });

    // Generate mock images with skin-tone silhouette and non-photo text document
    const genScript = `
import cv2
import numpy as np
import sys

# Create 400x500 portrait canvas (Aspect ratio 0.80)
h, w = 500, 400
img = np.full((h, w, 3), (240, 240, 240), dtype=np.uint8)

# Draw shoulders / shirt
cv2.ellipse(img, (200, 480), (140, 100), 0, 0, 360, (50, 60, 140), -1)

# Draw neck & head with skin tone (BGR: 160, 190, 220)
cv2.rectangle(img, (170, 300), (230, 380), (160, 190, 220), -1)
cv2.ellipse(img, (200, 220), (70, 95), 0, 0, 360, (160, 190, 220), -1)

# Draw hair
cv2.ellipse(img, (200, 160), (75, 45), 0, 0, 180, (30, 30, 30), -1)

cv2.imwrite(sys.argv[1], img)

# Create a non-photo document image
doc_img = np.full((600, 400, 3), 255, dtype=np.uint8)
cv2.putText(doc_img, "GOVERNMENT ELECTRICITY BILL", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
cv2.imwrite(sys.argv[2], doc_img)
`;

    fs.writeFileSync(path.join(testDir, 'gen_mock.py'), genScript);
    execSync(`python "${path.join(testDir, 'gen_mock.py')}" "${mockPassportImg}" "${mockDocImg}"`);
  });

  afterAll(() => {
    try {
      fs.rmSync(testDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    } catch {}
  });

  test('should detect passport photo geometry via tryPassportPhotoDetector', () => {
    const result = tryPassportPhotoDetector(mockPassportImg);
    expect(result.isPassport).toBe(true);
    expect(result.confidence).toBeGreaterThan(0.6);
  });

  test('should reject text document with no face via tryPassportPhotoDetector', () => {
    const result = tryPassportPhotoDetector(mockDocImg);
    expect(result.isPassport).toBe(false);
  });

  test('should classify text rule for passport photo', () => {
    const classification = classifyDocumentText('AFFIX RECENT PASSPORT SIZE PHOTOGRAPH OF APPLICANT');
    expect(classification.docType).toBe('passport_photo');
    expect(classification.docTypeName).toBe('Passport Size Photo');
  });

  test('should classify scanned passport photo via full processDocumentImage pipeline', async () => {
    const scanResult = await processDocumentImage(mockPassportImg, { autoRename: false });
    expect(scanResult.classification.docType).toBe('passport_photo');
    expect(scanResult.classification.docTypeName).toBe('Passport Size Photo');
  }, 30000);

  test('should generate white background copy with 50% resize and max 50KB', async () => {
    const whiteBgOutput = path.join(testDir, 'sample_passport_photo_white_bg.jpg');
    
    await processPhotoForUpload(mockPassportImg, {
      outputPath: whiteBgOutput,
      maxKB: 50,
      useAI: true
    });

    expect(fs.existsSync(whiteBgOutput)).toBe(true);
    const stats = fs.statSync(whiteBgOutput);
    expect(stats.size).toBeLessThanOrEqual(50 * 1024);
  }, 30000);
});
