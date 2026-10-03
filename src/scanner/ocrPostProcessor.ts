/**
 * OCR Post-Processing & Spell-Correction Engine.
 * Single Responsibility: Applies learned word replacements and character disambiguation rules to raw OCR text,
 * and persists new human-taught spell corrections.
 */
import * as fs from 'fs';
import * as path from 'path';

export interface SpellCorrectionsData {
  words: Record<string, string>;
  patterns: Array<{
    regex: string;
    replace: string;
    flags?: string;
  }>;
  last_updated?: string;
}

const SPELL_CORRECTIONS_FILE = path.resolve(path.join(__dirname, '../../dataset/ocr_spell_corrections.json'));

let _cachedCorrections: SpellCorrectionsData | null = null;

export function loadSpellCorrections(): SpellCorrectionsData {
  if (_cachedCorrections) return _cachedCorrections;

  if (fs.existsSync(SPELL_CORRECTIONS_FILE)) {
    try {
      const raw = fs.readFileSync(SPELL_CORRECTIONS_FILE, 'utf-8');
      _cachedCorrections = JSON.parse(raw) as SpellCorrectionsData;
      return _cachedCorrections;
    } catch (e) {
      console.warn('⚠️ Failed to parse ocr_spell_corrections.json:', e);
    }
  }

  _cachedCorrections = { words: {}, patterns: [] };
  return _cachedCorrections;
}

/**
 * Applies learned dictionary replacements and regex repairs to raw OCR text.
 */
export function applyOcrPostProcessing(rawText: string): string {
  if (!rawText) return rawText;

  const corrections = loadSpellCorrections();
  let processed = rawText;

  // 1. Apply regex repairs (e.g. O1/01/2000 -> 01/01/2000)
  if (corrections.patterns && corrections.patterns.length > 0) {
    for (const pat of corrections.patterns) {
      try {
        const re = new RegExp(pat.regex, pat.flags || 'g');
        processed = processed.replace(re, pat.replace);
      } catch (err) {
        // Ignore invalid regex patterns
      }
    }
  }

  // 2. Word-level replacements (case-insensitive word boundary replacement)
  if (corrections.words && Object.keys(corrections.words).length > 0) {
    for (const [misread, replacement] of Object.entries(corrections.words)) {
      if (!misread || !replacement || misread.toLowerCase() === replacement.toLowerCase()) continue;
      const wordRe = new RegExp(`\\b${escapeRegExp(misread)}\\b`, 'gi');
      processed = processed.replace(wordRe, replacement);
    }
  }

  return processed;
}

/**
 * Teaches the engine a new word replacement learned from user review.
 */
export function recordSpellCorrection(original: string, corrected: string): boolean {
  const origClean = original.trim().toLowerCase();
  const corrClean = corrected.trim();

  if (!origClean || !corrClean || origClean === corrClean.toLowerCase()) {
    return false;
  }

  const data = loadSpellCorrections();
  data.words[origClean] = corrClean;
  data.last_updated = new Date().toISOString();

  try {
    const parentDir = path.dirname(SPELL_CORRECTIONS_FILE);
    if (!fs.existsSync(parentDir)) {
      fs.mkdirSync(parentDir, { recursive: true });
    }
    fs.writeFileSync(SPELL_CORRECTIONS_FILE, JSON.stringify(data, null, 2), 'utf-8');
    _cachedCorrections = data;
    return true;
  } catch (e) {
    console.error('❌ Failed to save ocr_spell_corrections.json:', e);
    return false;
  }
}

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
