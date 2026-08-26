import { describe, test, expect, beforeAll, afterAll } from 'bun:test';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'child_process';
import { trySignatureDetector, processDocumentImage } from '../src/scanner/documentScanner';
import { extractPersonNameFromDirectory, classifyDocumentText } from '../src/classifier';

const testDir = path.resolve('./tests/mock_sig_test');
const personDir = path.join(testDir, 'Vijaykumar Tripathi');
const mockSignatureImg = path.join(personDir, 'scan_9912.jpg');
const mockDocImg = path.join(personDir, 'bill_sample.jpg');

describe('Signature Detector & Directory Person-Name Classifier', () => {
  beforeAll(() => {
    fs.mkdirSync(personDir, { recursive: true });

    // Generate mock blue-ink signature on white rectangular canvas + non-signature document
    const genScript = `
import cv2
import numpy as np
import sys

# 1. Create a wide rectangular signature image (500x180, aspect ratio ~ 2.77)
h, w = 180, 500
img = np.full((h, w, 3), 250, dtype=np.uint8) # light background

# Draw blue cursive ink strokes (BGR: Blue=180, Green=80, Red=20)
pts = np.array([[60, 90], [110, 45], [160, 130], [210, 60], [260, 110], [310, 50], [360, 120], [440, 80]], np.int32)
cv2.polylines(img, [pts], False, (180, 80, 20), 4, cv2.LINE_AA)
cv2.circle(img, (210, 70), 22, (170, 70, 15), 3)

cv2.imwrite(sys.argv[1], img)

# 2. Create a non-signature document image
doc_img = np.full((600, 450, 3), 255, dtype=np.uint8)
cv2.putText(doc_img, "GOVERNMENT ELECTRICITY DEPARTMENT", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
cv2.imwrite(sys.argv[2], doc_img)
`;

    fs.writeFileSync(path.join(testDir, 'gen_sig.py'), genScript);
    execSync(`python "${path.join(testDir, 'gen_sig.py')}" "${mockSignatureImg}" "${mockDocImg}"`);
  });

  afterAll(() => {
    try {
      fs.rmSync(testDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    } catch {}
  });

  test('should extract person name from folder hierarchy', () => {
    const p1 = 'C:\\Users\\Anosh\\My Drive (citizen@example.com)\\Work\\Residence\\2026\\8\\Vijaykumar Tripathi';
    expect(extractPersonNameFromDirectory(p1)).toBe('vijaykumar_tripathi');

    const p2 = 'C:/Users/Anosh/My Drive (citizen@example.com)/Work/PCC/2026/8/Rohan Gawde';
    expect(extractPersonNameFromDirectory(p2)).toBe('rohan_gawde');

    const p3 = 'C:/Users/Anosh/Documents/Notes/Projects/goaOnAuto/work_directory';
    expect(extractPersonNameFromDirectory(p3)).toBeUndefined();
  });

  test('should detect blue ink rectangular signature via trySignatureDetector', () => {
    const result = trySignatureDetector(mockSignatureImg);
    expect(result.isSignature).toBe(true);
    expect(result.confidence).toBeGreaterThanOrEqual(0.8);
    expect(result.inkType).toBe('blue_ink');
  });

  test('should reject full document from signature detector', () => {
    const result = trySignatureDetector(mockDocImg);
    expect(result.isSignature).toBe(false);
  });

  test('should classify text rule for signature', () => {
    const classification = classifyDocumentText('SPECIMEN SIGNATURE OF APPLICANT');
    expect(classification.docType).toBe('signature');
    expect(classification.docTypeName).toBe('Signature');
  });

  test('should classify scanned signature with person name from directory', async () => {
    const scanResult = await processDocumentImage(mockSignatureImg, { 
      autoRename: false,
      targetDir: personDir
    });

    expect(scanResult.classification.docType).toBe('signature');
    expect(scanResult.classification.docTypeName).toBe('Signature');
    expect(scanResult.classification.extractedName).toBe('vijaykumar_tripathi');
    expect(scanResult.classification.suggestedFilename).toBe('signature_vijaykumar_tripathi.jpg');
  }, 30000);
});
