/**
 * Person & Beneficiary Name Extraction Module.
 * Single Responsibility: Extracts person names from OCR document lines and directory path hierarchy.
 */

const GENERIC_FOLDER_NAMES = new Set([
  'work', 'residence', 'pcc', 'caste', 'caste_certificate', 'obc', 'marriage',
  'income', 'scans', 'downloads', 'documents', 'my drive', 'google drive',
  'desktop', 'goaonauto', 'work_directory', 'photos', 'images', 'temp', 'stage',
  'tests', 'mock_photo_test', 'mock_work_dir', 'mock_sig_test', 'projects', 'notes',
  'users', 'program files', 'appdata', 'local', 'roaming'
]);

function sanitizeExtractedSegment(raw: string): string | undefined {
  if (!raw) return undefined;
  // Remove common document title prefixes like "Mast. / Miss", "Shri / Smt / Kum", "Mr / Mrs / Miss"
  const stripped = raw
    .replace(/^(mast|master|miss|mr|mrs|ms|shri|smt|kumari)\.?\s*[\/\\]?\s*(miss|mast|master|smt|kumari)?\.?\s*/i, '')
    .trim();

  const safe = stripped
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, ' ')
    .split(/\s+/)
    .filter(word => word.length > 0 && !/^(mast|master|miss|mr|mrs|ms|shri|smt|kumari|\/|\\)$/i.test(word))
    .slice(0, 3)
    .join('_');

  return safe.length >= 2 ? safe : undefined;
}

/**
 * Extracts candidate person name from OCR text lines
 */
export function extractCandidateName(lines: string[], docType: string): string | undefined {
  const nameMarkers = [/name\s*[:\-]/i, /this is to certify that\s+/i, /shri\/smt\/kumari/i, /holder name\s*[:\-]/i];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;

    for (const marker of nameMarkers) {
      if (marker.test(line)) {
        const parts = line.split(marker);
        const matchPart = parts[1];
        const cleaned = matchPart ? sanitizeExtractedSegment(matchPart) : undefined;
        if (cleaned) {
          return cleaned;
        }
        const nextLine = lines[i + 1];
        const nextCleaned = nextLine ? sanitizeExtractedSegment(nextLine) : undefined;
        if (nextCleaned) {
          return nextCleaned;
        }
      }
    }
  }

  // Fallback for Aadhaar (line directly preceding DOB)
  if (docType === 'aadhaar') {
    const dobIndex = lines.findIndex(l => /dob|date of birth|year of birth/i.test(l));
    if (dobIndex > 0) {
      const prevLine = lines[dobIndex - 1];
      if (prevLine) {
        const cleaned = sanitizeExtractedSegment(prevLine);
        if (cleaned) return cleaned;
      }
    }
  }

  return undefined;
}

/**
 * Extracts candidate person name from directory hierarchy path
 */
export function extractPersonNameFromDirectory(dirPath: string): string | undefined {
  if (!dirPath) return undefined;
  const segments = dirPath.split(/[\\/]/).map(s => s.trim()).filter(Boolean);

  const searchLimit = Math.max(0, segments.length - 3);

  for (let i = segments.length - 1; i >= searchLimit; i--) {
    const seg = segments[i];
    if (!seg) continue;
    if (/^\d+$/.test(seg)) continue;
    if (seg.includes('@') || /my drive/i.test(seg)) continue;
    if (GENERIC_FOLDER_NAMES.has(seg.toLowerCase())) continue;

    if (/[a-zA-Z]{2,}/.test(seg)) {
      return seg.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '').toLowerCase();
    }
  }
  return undefined;
}
