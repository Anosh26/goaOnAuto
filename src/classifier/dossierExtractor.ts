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
 * Deduces DOB and Age from text.
 */
function deduceDOB(text: string, filePath: string): { dob?: DossierField<string>; age?: DossierField<number> } {
  // DD/MM/YYYY or DD-MM-YYYY
  const dobMatch = text.match(/\b(\d{2}[/-]\d{2}[/-]\d{4})\b/);
  if (dobMatch && dobMatch[1]) {
    const dobStr = dobMatch[1].replace(/\//g, '-');
    const year = parseInt(dobStr.substring(6, 10), 10);
    const age = new Date().getFullYear() - year;
    
    return {
      dob: { value: dobStr, confidence: 0.8, sourceDoc: filePath },
      age: { value: age, confidence: 0.8, sourceDoc: filePath }
    };
  }
  return {};
}

/**
 * Synthesizes final ApplicantDossier using Aadhaar QR as Golden source (if available),
 * falling back to OCR text extraction for missing fields (like Years in Goa).
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
      const yearStr = qrResult.dob.split('-').pop();
      if (yearStr) {
        dossier.age = { 
          value: new Date().getFullYear() - parseInt(yearStr, 10), 
          confidence: 1.0, 
          sourceDoc: 'Aadhaar QR (Calculated)' 
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
      const deduced = deduceDOB(doc.rawText, doc.filePath);
      if (deduced.dob) dossier.dob = deduced.dob;
      if (deduced.age) dossier.age = deduced.age;
    }

    // Deduced Years in Goa (Aadhaar QR never has this, always extracted via OCR)
    const years = deduceYearsInGoa(doc.rawText, doc.docType, doc.filePath);
    if (years) {
      // Prioritize higher confidence (Residence Cert > Bonafide) or strictly larger duration?
      if (!bestYearsInGoa || years.confidence > bestYearsInGoa.confidence || (years.confidence === bestYearsInGoa.confidence && years.value > bestYearsInGoa.value)) {
        bestYearsInGoa = years;
      }
    }
  }

  if (bestYearsInGoa) {
    dossier.yearsInGoa = bestYearsInGoa;
  }

  return dossier;
}
