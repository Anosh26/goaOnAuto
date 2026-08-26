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
