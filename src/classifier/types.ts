/**
 * Document Classification Types & Interfaces.
 * Single Responsibility: Defines data structures for classification rules and results.
 */

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

export interface DossierField<T> {
  value: T;
  confidence: number;
  sourceDoc: string;
  evidenceText?: string;
}

export interface ApplicantDossier {
  name?: DossierField<string>;
  dob?: DossierField<string>;
  age?: DossierField<number>;
  address?: DossierField<{
    full: string;
    houseNo?: string;
    villageOrCity?: string;
    taluka?: string;
    pincode?: string;
    state?: string;
  }>;
  yearsInGoa?: DossierField<number>;
  gender?: DossierField<string>;
}
