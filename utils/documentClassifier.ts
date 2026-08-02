export interface DocumentTypeRule {
  id: string;
  name: string;
  keywords: string[];
  patterns?: RegExp[];
  priority?: number;
}

export interface ClassificationResult {
  docType: string;
  docTypeName: string;
  extractedName?: string;
  matchedKeywords: string[];
  confidence: number;
  suggestedFilename: string;
}

export const DOCUMENT_RULES: DocumentTypeRule[] = [
  {
    id: 'aadhaar',
    name: 'Aadhaar Card',
    keywords: ['unique identification authority', 'government of india', 'aadhaar', 'uidai', 'year of birth'],
    patterns: [/\b\d{4}\s?\d{4}\s?\d{4}\b/],
    priority: 10
  },
  {
    id: 'pan',
    name: 'PAN Card',
    keywords: ['income tax department', 'govt of india', 'permanent account number', 'pan card'],
    patterns: [/\b[A-Z]{5}[0-9]{4}[A-Z]\b/],
    priority: 10
  },
  {
    id: 'driving_license',
    name: 'Driving License',
    keywords: ['driving licence', 'transport department', 'licence no', 'dl no', 'form 7'],
    patterns: [/\b[A-Z]{2}[- ]?\d{2}[- ]?\d{11}\b/i],
    priority: 9
  },
  {
    id: 'passport',
    name: 'Passport',
    keywords: ['republic of india', 'passport no', 'passport', 'type p'],
    patterns: [/\b[A-Z][0-9]{7}\b/],
    priority: 9
  },
  {
    id: 'voter_id',
    name: 'Voter ID Card',
    keywords: [
      'election commission of india', 
      'election commission', 
      'elector identity card', 
      'identity card',
      'voter id', 
      'voter', 
      'epic', 
      'epic no', 
      'epic number', 
      'electoral registration officer', 
      'assembly constituency'
    ],
    patterns: [/\b[A-Z]{3}[0-9]{7}\b/i],
    priority: 10
  },
  {
    id: 'marriage_cert',
    name: 'Marriage Certificate',
    keywords: ['marriage certificate', 'certificate of marriage', 'civil registration', 'civil registrar', 'office of civil registrar', 'solemnization of marriage', 'registrar of marriages', 'form no 16', 'groom', 'bride'],
    priority: 8
  },
  {
    id: 'birth_cert',
    name: 'Birth Certificate',
    keywords: ['birth certificate', 'certificate of birth', 'registration of births and deaths', 'date of birth', 'form no 5', 'name of child', 'place of birth'],
    priority: 8
  },
  {
    id: 'bonafide_cert',
    name: 'Bonafide Certificate',
    keywords: ['bonafide certificate', 'bonafide student', 'this is to certify that', 'regular student', 'academic year', 'roll no', 'school', 'college'],
    priority: 8
  },
  {
    id: 'electricity_bill',
    name: 'Electricity Bill',
    keywords: ['electricity department', 'electricity bill', 'units consumed', 'kwh', 'consumer no', 'ca no', 'bill amount', 'power distribution'],
    priority: 8
  },
  {
    id: 'house_tax',
    name: 'House Tax / Property Tax',
    keywords: ['house tax', 'property tax', 'village panchayat', 'municipal council', 'tax receipt', 'assessment year', 'house no'],
    priority: 8
  },
  {
    id: 'residence_cert',
    name: 'Residence Certificate',
    keywords: ['residence certificate', 'certificate of residence', 'resident of', 'mamlatdar', 'sub divisional officer', 'residing at'],
    priority: 8
  },
  {
    id: 'caste_cert',
    name: 'Caste Certificate',
    keywords: ['caste certificate', 'community certificate', 'scheduled caste', 'scheduled tribe', 'other backward class', 'obc', 'belongs to caste'],
    priority: 8
  },
  {
    id: 'samaj_cert',
    name: 'Samaj Certificate',
    keywords: ['samaj certificate', 'samaj', 'sanstha', 'community association', 'samajik', 'trust'],
    priority: 7
  },
  {
    id: 'ration_card',
    name: 'Ration Card',
    keywords: ['ration card', 'civil supplies', 'food and civil supplies', 'head of family', 'fps', 'card no', 'aph', 'phh', 'nphh'],
    priority: 8
  },
  {
    id: 'pcc',
    name: 'Police Clearance Certificate (PCC)',
    keywords: ['police clearance certificate', 'police clearance', 'pcc', 'police station', 'passport office', 'no criminal record'],
    priority: 9
  },
  {
    id: 'obc_cert',
    name: 'OBC Certificate',
    keywords: ['other backward class', 'obc certificate', 'obc', 'creamy layer', 'non creamy layer'],
    priority: 9
  },
  {
    id: 'marksheet',
    name: 'Marksheet / Academic Certificate',
    keywords: ['marks statement', 'marksheet', 'board of secondary education', 'statement of marks', 'passing certificate', 'grade card', 'marks obtained'],
    priority: 7
  }
];

export function classifyDocumentText(rawText: string, originalFilename: string = '', dirPathHint: string = ''): ClassificationResult {
  const normalizedText = rawText.toLowerCase();
  const normalizedPath = dirPathHint.toLowerCase();
  const lines = rawText.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

  let bestMatch: DocumentTypeRule | null = null;
  let maxScore = 0;
  let matchedKeywords: string[] = [];

  for (const rule of DOCUMENT_RULES) {
    let score = 0;
    const currentMatched: string[] = [];

    // Check directory path hint match (e.g. folder named 'pcc', 'residence', 'caste')
    if (normalizedPath) {
      if (normalizedPath.includes(rule.id) || rule.keywords.some(kw => normalizedPath.includes(kw.toLowerCase()))) {
        score += 4;
        currentMatched.push(`dir_hint:${rule.id}`);
      }
    }

    // Check keywords
    for (const kw of rule.keywords) {
      if (normalizedText.includes(kw.toLowerCase())) {
        score += 2;
        currentMatched.push(kw);
      }
    }

    // Check regex patterns
    if (rule.patterns) {
      for (const pattern of rule.patterns) {
        if (pattern.test(rawText)) {
          score += 5; // Heavy weight for regex match
          currentMatched.push(`pattern:${pattern.source}`);
        }
      }
    }

    // Apply priority weighting
    if (score > 0) {
      score += (rule.priority || 5);
    }

    if (score > maxScore) {
      maxScore = score;
      bestMatch = rule;
      matchedKeywords = currentMatched;
    }
  }

  const docType = bestMatch ? bestMatch.id : 'document';
  const docTypeName = bestMatch ? bestMatch.name : 'Unknown Document';
  const extractedName = extractCandidateName(lines, docType);
  
  const ext = originalFilename.includes('.') ? originalFilename.substring(originalFilename.lastIndexOf('.')) : '.jpg';
  
  const safeNameStr = extractedName
    ? extractedName.toLowerCase().replace(/[^a-z0-9]/g, '_').replace(/_+/g, '_').replace(/^_+|_+$/g, '')
    : '';

  const filenameStem = safeNameStr ? `${docType}_${safeNameStr}` : `${docType}_scanned`;
  const suggestedFilename = `${filenameStem}${ext}`;

  return {
    docType,
    docTypeName,
    extractedName,
    matchedKeywords,
    confidence: maxScore > 10 ? 0.9 : maxScore > 5 ? 0.7 : 0.4,
    suggestedFilename
  };
}

function extractCandidateName(lines: string[], docType: string): string | undefined {
  // Common name markers in Indian documents
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

  // Fallback for Aadhaar (line above DOB)
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
