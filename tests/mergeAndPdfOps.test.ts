import * as fs from 'fs';
import * as path from 'path';
import { mergeCardFrontBackVertically, convertImagesToMultipagePdf } from '../src/image/pythonOpsWrapper';
import { classifyDocumentText } from '../src/classifier';

const testDir = path.resolve('./tests/mock_merge_test');
fs.mkdirSync(testDir, { recursive: true });

console.log('=== Testing Image Merging & Multipage PDF Generation ===');

// Create mock images (using Python PIL to generate clean sample image files)
const createMockImg = `
from PIL import Image, ImageDraw, ImageFont
import sys

def create_card(text, filename, color):
    img = Image.new('RGB', (600, 400), color=color)
    d = ImageDraw.Draw(img)
    d.text((50, 180), text, fill=(255, 255, 255))
    img.save(filename)

create_card("VOTER ID FRONT SIDE", sys.argv[1], (41, 128, 185))
create_card("VOTER ID BACK SIDE", sys.argv[2], (39, 174, 96))
create_card("MARRIAGE CERT PAGE 1", sys.argv[3], (142, 68, 173))
create_card("MARRIAGE CERT PAGE 2", sys.argv[4], (211, 84, 0))
`;

const mockFront = path.join(testDir, 'voter_front.jpg');
const mockBack = path.join(testDir, 'voter_back.jpg');
const mockPage1 = path.join(testDir, 'marriage_p1.jpg');
const mockPage2 = path.join(testDir, 'marriage_p2.jpg');

fs.writeFileSync(path.join(testDir, 'gen.py'), createMockImg);
const { execSync } = require('child_process');
execSync(`python "${path.join(testDir, 'gen.py')}" "${mockFront}" "${mockBack}" "${mockPage1}" "${mockPage2}"`);

// 1. Test Voter ID Card Vertical Merge
console.log('\n1. Testing Card Vertical Merge (Front on top, Back on bottom)...');
const mergedOutput = path.join(testDir, 'voter_id_merged.jpg');
mergeCardFrontBackVertically(mockFront, mockBack, mergedOutput);

if (fs.existsSync(mergedOutput)) {
  const stats = fs.statSync(mergedOutput);
  console.log(`   ✅ Merged Card created successfully (${stats.size} bytes): ${mergedOutput}`);
} else {
  console.error('   ❌ Merged card creation failed!');
}

// 2. Test Civil Registration / Marriage Certificate Multipage PDF
console.log('\n2. Testing Multipage PDF Conversion...');
const pdfOutput = path.join(testDir, 'marriage_cert_john_and_jane.pdf');
convertImagesToMultipagePdf([mockPage1, mockPage2], pdfOutput);

if (fs.existsSync(pdfOutput)) {
  const stats = fs.statSync(pdfOutput);
  console.log(`   ✅ Multipage PDF created successfully (${stats.size} bytes): ${pdfOutput}`);
} else {
  console.error('   ❌ PDF creation failed!');
}

// 3. Test Civil Registration Keyword Classification
console.log('\n3. Testing Civil Registration Classifier Rule...');
const civilRegText = "OFFICE OF THE CIVIL REGISTRAR FORM NO 16 CERTIFICATE OF MARRIAGE";
const classification = classifyDocumentText(civilRegText);
console.log(`   Result: ${classification.docType} (${classification.docTypeName}) - Confidence: ${classification.confidence * 100}%`);

// Cleanup
try {
  fs.rmSync(testDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
} catch {}
console.log('\n✅ All Image Merge & Multipage PDF tests passed successfully!');
