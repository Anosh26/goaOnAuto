/**
 * Document Classifier Engine.
 * Single Responsibility: Evaluates raw OCR text and directory context against rules to produce a classification result.
 */
import { ClassificationResult, DocumentTypeRule } from './types';
import { DOCUMENT_RULES } from './rules';
import { extractCandidateName } from './nameExtractor';

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

    // Check directory path hint match
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
          score += 5;
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

export * from './types';
export * from './rules';
export * from './nameExtractor';
