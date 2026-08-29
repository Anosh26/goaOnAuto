/**
 * Document Classifier Engine.
 * Single Responsibility: Evaluates raw OCR text and directory context against rules to produce a classification result.
 * Enhanced: Loads learned weights from human corrections to boost/suppress keyword scoring.
 */
import * as fs from 'fs';
import * as path from 'path';
import { ClassificationResult, DocumentTypeRule } from './types';
import { DOCUMENT_RULES } from './rules';
import { extractCandidateName } from './nameExtractor';

// --- Learned Weights System (from human corrections via retrain_classifier.ts) ---

interface LearnedCategoryWeight {
  boost_keywords: string[];
  suppress_keywords: string[];
  priority_adjustment: number;
  confusion_sources: Record<string, number>;
  total_confirmed: number;
  total_corrected: number;
}

interface LearnedWeights {
  generated_at: string;
  total_corrections_analysed: number;
  overall_ai_accuracy: number;
  categories: Record<string, LearnedCategoryWeight>;
}

let _learnedWeights: LearnedWeights | null = null;
let _learnedWeightsLoaded = false;

function loadLearnedWeights(): LearnedWeights | null {
  if (_learnedWeightsLoaded) return _learnedWeights;
  _learnedWeightsLoaded = true;

  const weightsPath = path.resolve(path.join(__dirname, '../../dataset/learned_weights.json'));
  if (fs.existsSync(weightsPath)) {
    try {
      const raw = fs.readFileSync(weightsPath, 'utf-8');
      _learnedWeights = JSON.parse(raw) as LearnedWeights;
      console.log(`   📚 Loaded learned weights (${_learnedWeights.total_corrections_analysed} corrections, ${_learnedWeights.overall_ai_accuracy}% AI accuracy)`);
    } catch (e) {
      console.warn('   ⚠️ Failed to parse learned_weights.json:', e);
    }
  }
  return _learnedWeights;
}

export function classifyDocumentText(rawText: string, originalFilename: string = '', dirPathHint: string = ''): ClassificationResult {
  const normalizedText = rawText.toLowerCase();
  const normalizedPath = dirPathHint.toLowerCase();
  const lines = rawText.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

  // Load learned weights (cached after first load)
  const learnedWeights = loadLearnedWeights();

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

    // --- Apply learned weight adjustments from human corrections ---
    if (learnedWeights && learnedWeights.categories[rule.id]) {
      const catWeights = learnedWeights.categories[rule.id]!;

      // Boost keywords: extra +3 points per boosted keyword found in text
      for (const boostKw of catWeights.boost_keywords) {
        if (normalizedText.includes(boostKw.toLowerCase())) {
          score += 3;
          currentMatched.push(`learned_boost:${boostKw}`);
        }
      }

      // Suppress keywords: penalty of -2 per suppressed keyword found in text
      for (const suppressKw of catWeights.suppress_keywords) {
        if (normalizedText.includes(suppressKw.toLowerCase())) {
          score -= 2;
          currentMatched.push(`learned_suppress:${suppressKw}`);
        }
      }

      // Priority adjustment from correction frequency
      if (score > 0 && catWeights.priority_adjustment > 0) {
        score += catWeights.priority_adjustment;
      }
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
