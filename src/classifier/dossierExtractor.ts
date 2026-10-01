import { ApplicantDossier, DossierField } from './types';
import { AadhaarQrResult } from '../scanner/gpuDaemonClient';

export interface ExtractedDocument {
  docType: string;
  docTypeName: string;
  rawText: string;
  filePath: string;
  extractedName?: string;
}

/**
 * Deduces the number of years lived in Goa/Address from document text.
 */
function deduceYearsInGoa(text: string, docType: string, filePath: string): DossierField<number> | undefined {
  const normalized = text.toLowerCase().replace(/\s+/g, ' ');

  if (docType === 'residence_cert') {
    // Pattern 1: "for the last 15 years" or "past 15 years"
    const durationMatch = normalized.match(/(?:for|past|last)\s+(?:the\s+)?(?:past|last)?\s*(\d{1,2})\s*years?/);
    if (durationMatch && durationMatch[1]) {
      return {
        value: parseInt(durationMatch[1], 10),
        confidence: 0.9,
        sourceDoc: filePath,
        evidenceText: durationMatch[0]
      };
    }

    // Pattern 2: "residing since 2010"
    const sinceMatch = normalized.match(/since\s+(?:the\s+year\s+)?(19\d{2}|20\d{2})/);
    if (sinceMatch && sinceMatch[1]) {
      const year = parseInt(sinceMatch[1], 10);
      const currentYear = new Date().getFullYear();
      return {
        value: currentYear - year,
        confidence: 0.85,
        sourceDoc: filePath,
        evidenceText: sinceMatch[0]
      };
    }
  }

  if (docType === 'bonafide_cert' || docType === 'marksheet') {
    // Pattern: "from 2012 to 2024"
    const spanMatch = normalized.match(/from\s+(20\d{2})\s+to\s+(20\d{2})/);
    if (spanMatch && spanMatch[1] && spanMatch[2]) {
      const start = parseInt(spanMatch[1], 10);
      const end = parseInt(spanMatch[2], 10);
      return {
        value: end - start,
        confidence: 0.8,
        sourceDoc: filePath,
        evidenceText: spanMatch[0]
      };
    }
  }

  return undefined;
}

/**
 * Calculates person's age from various DOB formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, YYYY).
 */
export function calculateAgeFromDob(dobStr: string): number | undefined {
  if (!dobStr) return undefined;
  const cleaned = dobStr.trim();

  // 1. DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
  const dmyMatch = cleaned.match(/^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$/);
  if (dmyMatch && dmyMatch[1] && dmyMatch[2] && dmyMatch[3]) {
    const day = parseInt(dmyMatch[1], 10);
    const month = parseInt(dmyMatch[2], 10);
    const year = parseInt(dmyMatch[3], 10);
    const birthDate = new Date(year, month - 1, day);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age >= 0 && age <= 130 ? age : undefined;
  }

  // 2. YYYY-MM-DD or YYYY/MM/DD
  const ymdMatch = cleaned.match(/^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$/);
  if (ymdMatch && ymdMatch[1] && ymdMatch[2] && ymdMatch[3]) {
    const year = parseInt(ymdMatch[1], 10);
    const month = parseInt(ymdMatch[2], 10);
    const day = parseInt(ymdMatch[3], 10);
    const birthDate = new Date(year, month - 1, day);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const m = today.getMonth() - birthDate.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age >= 0 && age <= 130 ? age : undefined;
  }

  // 3. 4-digit year only (e.g. YOB: 1998)
  const yMatch = cleaned.match(/\b(19\d{2}|20\d{2})\b/);
  if (yMatch && yMatch[1]) {
    const year = parseInt(yMatch[1], 10);
    const age = new Date().getFullYear() - year;
    return age >= 0 && age <= 130 ? age : undefined;
  }

  return undefined;
}

/**
 * Deduces DOB and Age from text with high precision.
 * Prioritizes explicit DOB labels and birth certificates over random document dates.
 */
function deduceDOB(text: string, filePath: string, docType?: string): { dob?: DossierField<string>; age?: DossierField<number> } {
  if (!text) return {};

  // Priority 1: Explicit DOB labels (English, Hindi, Marathi)
  const labeledMatch = text.match(/(?:DOB|D\.O\.B|Date of Birth|Birth Date|जन्म\s*तारीख|जन्म\s*तिथि|जन्म\s*दिनांक|born\s*on)[\s\:\-\.\/]*([0-3]?\d[\/\-\.][0-1]?\d[\/\-\.]\d{4})/i);
  if (labeledMatch && labeledMatch[1]) {
    const dobStr = labeledMatch[1].replace(/\./g, '/').replace(/-/g, '/');
    const age = calculateAgeFromDob(dobStr);
    if (age !== undefined) {
      return {
        dob: { value: dobStr, confidence: 0.95, sourceDoc: filePath, evidenceText: labeledMatch[0] },
        age: { value: age, confidence: 0.95, sourceDoc: filePath }
      };
    }
  }

  // Priority 2: Year of Birth label (e.g. YOB: 1999)
  const yobMatch = text.match(/(?:Year of Birth|YOB|जन्म\s*वर्ष)[\s\:\-\.]*(\d{4})/i);
  if (yobMatch && yobMatch[1]) {
    const year = parseInt(yobMatch[1], 10);
    const currentYear = new Date().getFullYear();
    const age = currentYear - year;
    if (age >= 0 && age <= 120) {
      return {
        dob: { value: `01/01/${year}`, confidence: 0.85, sourceDoc: filePath, evidenceText: yobMatch[0] },
        age: { value: age, confidence: 0.85, sourceDoc: filePath }
      };
    }
  }

  // Priority 3: Only on Aadhaar or Birth Certificate, search for birth-plausible dates (year 1940 to present - 1)
  if (docType === 'aadhaar' || docType === 'birth_cert') {
    const allDates = text.matchAll(/\b([0-3]?\d[\/\-\.][0-1]?\d[\/\-\.](?:19\d{2}|20[0-2]\d))\b/g);
    for (const m of allDates) {
      const dStr = m[1]!.replace(/\./g, '/').replace(/-/g, '/');
      const age = calculateAgeFromDob(dStr);
      if (age !== undefined && age >= 1 && age <= 100) {
        return {
          dob: { value: dStr, confidence: 0.8, sourceDoc: filePath, evidenceText: m[0] },
          age: { value: age, confidence: 0.8, sourceDoc: filePath }
        };
      }
    }
  }

  return {};
}

/**
 * Extracts 12-digit Aadhaar Number from Golden Source QR or document OCR.
 */
function deduceAadhaarNumber(
  documents: ExtractedDocument[],
  qrResult?: AadhaarQrResult | null
): DossierField<string> | undefined {
  // 1. Aadhaar QR code Golden Source
  if (qrResult && qrResult.uid) {
    const raw = String(qrResult.uid).replace(/\D/g, '');
    if (raw.length === 12) {
      return {
        value: raw,
        confidence: 1.0,
        sourceDoc: 'Aadhaar QR (Golden Source)'
      };
    }
  }

  // 2. Scan documents prioritizing Aadhaar cards
  const sortedDocs = [...documents].sort((a, b) => (a.docType === 'aadhaar' ? -1 : 1));

  for (const doc of sortedDocs) {
    const text = doc.rawText;
    if (!text) continue;

    // Pattern 1: Explicitly labeled "Aadhaar No" followed by 12 digits
    const labeledMatch = text.match(/(?:Aadhaar|Aadhar|Adhar|UID|UIDAI)[\s\:\-\#No\.]*([2-9]\d{3}[\s\-_]*\d{4}[\s\-_]*\d{4})\b/i);
    if (labeledMatch && labeledMatch[1]) {
      const clean = labeledMatch[1].replace(/\D/g, '');
      if (clean.length === 12 && clean[0] !== '0' && clean[0] !== '1') {
        return {
          value: clean,
          confidence: 0.95,
          sourceDoc: doc.filePath,
          evidenceText: labeledMatch[0]
        };
      }
    }

    // Pattern 2: Standard 3 groups of 4 digits (e.g. 2345 6789 0123)
    const groupMatch = text.match(/\b([2-9]\d{3})\s+(\d{4})\s+(\d{4})\b/);
    if (groupMatch && groupMatch[1] && groupMatch[2] && groupMatch[3]) {
      const clean = `${groupMatch[1]}${groupMatch[2]}${groupMatch[3]}`;
      return {
        value: clean,
        confidence: 0.9,
        sourceDoc: doc.filePath,
        evidenceText: groupMatch[0]
      };
    }

    // Pattern 3: Any 12 consecutive digits on Aadhaar document
    if (doc.docType === 'aadhaar') {
      const any12Match = text.match(/\b([2-9]\d{11})\b/);
      if (any12Match && any12Match[1]) {
        return {
          value: any12Match[1],
          confidence: 0.85,
          sourceDoc: doc.filePath,
          evidenceText: any12Match[0]
        };
      }
    }
  }

  return undefined;
}

/**
 * Extracts Previous Residence Certificate records (number, issue date, authority).
 */
function deducePreviousResidenceCert(documents: ExtractedDocument[]): {
  hasPreviousResidenceCert: boolean;
  certNumber?: string;
  issueDate?: string;
  authority?: string;
  sourceDoc?: string;
} {
  const resDoc = documents.find(d => d.docType === 'residence_cert' || /residence\s*certificate/i.test(d.rawText));
  if (!resDoc) {
    return { hasPreviousResidenceCert: false };
  }

  const text = resDoc.rawText;
  let certNumber: string | undefined;
  let issueDate: string | undefined;
  let authority: string | undefined;

  // Extract Certificate Number (e.g. "No. 3/15/2018-MAG/4521", "Certificate No: REV/05/2021/1234")
  const certNoMatch = text.match(/(?:Certificate\s*No\.?|Cert\.?\s*No\.?|Registration\s*No\.?|Inward\s*No\.?|File\s*No\.?|Ref\s*No\.?|No\.?)[\s\:\-\.]*([A-Za-z0-9\/\-_]{4,30})/i);
  if (certNoMatch && certNoMatch[1]) {
    certNumber = certNoMatch[1].trim();
  }

  // Extract Issue Date
  const dateMatch = text.match(/(?:Dated?|Date\s*of\s*Issue|Issue\s*Date|Date)[\s\:\-\.]*([0-3]?\d[\/\-\.][0-1]?\d[\/\-\.]\d{4})/i);
  if (dateMatch && dateMatch[1]) {
    issueDate = dateMatch[1].trim();
  }

  // Extract Authority (e.g. Mamlatdar of Bardez)
  const authMatch = text.match(/(?:Mamlatdar\s*of\s*[A-Za-z]+|Office\s*of\s*the\s*Mamlatdar|Sub[\s\-]Divisional\s*(?:Officer|Magistrate)|Collectorate)/i);
  if (authMatch) {
    authority = authMatch[0].trim();
  }

  return {
    hasPreviousResidenceCert: true,
    certNumber,
    issueDate,
    authority: authority || 'Office of the Mamlatdar',
    sourceDoc: resDoc.filePath
  };
}

/**
 * Synthesizes final ApplicantDossier using Aadhaar QR as Golden source (if available),
 * falling back to OCR text extraction for missing fields (like Years in Goa, Aadhaar No, and Previous Cert).
 */
export function synthesizeDossier(
  documents: ExtractedDocument[],
  qrResult?: AadhaarQrResult | null
): ApplicantDossier {
  const dossier: ApplicantDossier = {};

  // 1. Tier 1: Golden Source (Aadhaar QR)
  if (qrResult && qrResult.success) {
    if (qrResult.name) {
      dossier.name = { value: qrResult.name, confidence: 1.0, sourceDoc: 'Aadhaar QR' };
    }
    if (qrResult.dob) {
      dossier.dob = { value: qrResult.dob, confidence: 1.0, sourceDoc: 'Aadhaar QR' };
      const calculatedAge = calculateAgeFromDob(qrResult.dob);
      if (calculatedAge !== undefined) {
        dossier.age = { 
          value: calculatedAge, 
          confidence: 1.0, 
          sourceDoc: 'Aadhaar QR (Calculated from DOB)' 
        };
      }
    }
    if (qrResult.gender) {
      dossier.gender = { value: qrResult.gender, confidence: 1.0, sourceDoc: 'Aadhaar QR' };
    }
    
    const parts = [qrResult.house, qrResult.lm, qrResult.loc, qrResult.vtc, qrResult.dist, qrResult.state, qrResult.pc].filter(Boolean);
    if (parts.length > 0) {
      dossier.address = {
        value: {
          full: parts.join(', '),
          houseNo: qrResult.house,
          villageOrCity: qrResult.vtc || qrResult.loc,
          taluka: qrResult.subdist,
          pincode: qrResult.pc,
          state: qrResult.state
        },
        confidence: 1.0,
        sourceDoc: 'Aadhaar QR'
      };
    }
  }

  // 2. Tier 2: OCR Fallbacks & Multi-Document Deduction
  let bestYearsInGoa: DossierField<number> | undefined = undefined;

  for (const doc of documents) {
    // Deduced Name (if missing)
    if (!dossier.name && doc.extractedName) {
      dossier.name = { value: doc.extractedName, confidence: 0.7, sourceDoc: doc.filePath };
    }

    // Deduced DOB/Age (if missing)
    if (!dossier.dob) {
      const deduced = deduceDOB(doc.rawText, doc.filePath, doc.docType);
      if (deduced.dob) dossier.dob = deduced.dob;
      if (deduced.age) dossier.age = deduced.age;
    }

    // Deduced Years in Goa
    const years = deduceYearsInGoa(doc.rawText, doc.docType, doc.filePath);
    if (years) {
      if (!bestYearsInGoa || years.confidence > bestYearsInGoa.confidence || (years.confidence === bestYearsInGoa.confidence && years.value > bestYearsInGoa.value)) {
        bestYearsInGoa = years;
      }
    }
  }

  if (bestYearsInGoa) {
    dossier.yearsInGoa = bestYearsInGoa;
  }

  // 3. Aadhaar Number Deduction
  const aadhaarField = deduceAadhaarNumber(documents, qrResult);
  if (aadhaarField) {
    dossier.aadhaar = aadhaarField;
    dossier.idProofNumber = aadhaarField;
  }

  // 4. Previous Residence Certificate Extraction
  const prevCert = deducePreviousResidenceCert(documents);
  dossier.hasPreviousResidenceCert = prevCert.hasPreviousResidenceCert;
  if (prevCert.hasPreviousResidenceCert) {
    dossier.previousResidenceCert = {
      number: prevCert.certNumber,
      issueDate: prevCert.issueDate,
      authority: prevCert.authority,
      sourceDoc: prevCert.sourceDoc
    };
  }

  // 5. Detect photo and signature attachments
  const photoDoc = documents.find(d => d.docType === 'passport_photo');
  if (photoDoc && !dossier.photoPath) {
    dossier.photoPath = photoDoc.filePath;
  }
  const sigDoc = documents.find(d => d.docType === 'signature');
  if (sigDoc && !dossier.signaturePath) {
    dossier.signaturePath = sigDoc.filePath;
  }

  return dossier;
}
