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
        if (matchPart && matchPart.trim().length > 2) {
          return matchPart.trim().split(/\s+/).slice(0, 3).join('_');
        }
        const nextLine = lines[i + 1];
        if (nextLine && nextLine.trim().length > 2) {
          return nextLine.trim().split(/\s+/).slice(0, 3).join('_');
        }
      }
    }
  }

  // Fallback for Aadhaar (line directly preceding DOB)
  if (docType === 'aadhaar') {
    const dobIndex = lines.findIndex(l => /dob|date of birth|year of birth/i.test(l));
    if (dobIndex > 0) {
      const prevLine = lines[dobIndex - 1];
      if (prevLine && prevLine.trim().length > 3) {
        return prevLine.trim().split(/\s+/).slice(0, 3).join('_');
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
