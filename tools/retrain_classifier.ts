/**
 * Classifier Retraining Engine — Learns from Human Corrections & Custom Training Keywords.
 * Single Responsibility: Reads dataset/corrections.jsonl, analyses misclassification patterns,
 * incorporates explicit human keywords, and generates dataset/learned_weights.json.
 */
import * as fs from 'fs';
import * as path from 'path';
import { DOCUMENT_RULES } from '../src/classifier/rules';

interface CorrectionEntry {
  timestamp: string;
  filePath: string;
  fileName: string;
  aiDetected: string;
  aiDetectedName: string;
  aiConfidence: number;
  humanVerified: string;
  humanVerifiedName: string;
  action: 'confirmed' | 'changed' | 'skipped';
  extractedName: string;
  customKeyword?: string;
  matchedKeywords: string[];
}

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

function readCorrections(): CorrectionEntry[] {
  const correctionsPath = path.resolve('./dataset/corrections.jsonl');
  if (!fs.existsSync(correctionsPath)) {
    return [];
  }

  const lines = fs.readFileSync(correctionsPath, 'utf-8').split('\n').filter(Boolean);
  const entries: CorrectionEntry[] = [];

  for (const line of lines) {
    try {
      entries.push(JSON.parse(line));
    } catch {}
  }

  return entries;
}

function countDatasetFiles(): Record<string, number> {
  const counts: Record<string, number> = {};
  const datasetRawDir = path.resolve('./dataset/raw');

  if (!fs.existsSync(datasetRawDir)) return counts;

  const subDirs = fs.readdirSync(datasetRawDir, { withFileTypes: true });
  for (const sub of subDirs) {
    if (!sub.isDirectory()) continue;
    const catPath = path.join(datasetRawDir, sub.name);
    try {
      const files = fs.readdirSync(catPath).filter((f) => !f.startsWith('.'));
      counts[sub.name] = files.length;
    } catch {}
  }

  return counts;
}

function analyseCorrections(corrections: CorrectionEntry[]): LearnedWeights {
  const categoryStats: Record<
    string,
    {
      confirmed: number;
      corrected: number;
      confusionSources: Record<string, number>;
      correctedKeywords: string[];
      confirmedKeywords: string[];
      explicitUserKeywords: Set<string>;
    }
  > = {};

  // Initialise stats for all known categories
  for (const rule of DOCUMENT_RULES) {
    categoryStats[rule.id] = {
      confirmed: 0,
      corrected: 0,
      confusionSources: {},
      correctedKeywords: [],
      confirmedKeywords: [],
      explicitUserKeywords: new Set<string>(),
    };
  }

  let totalConfirmed = 0;
  let totalChanged = 0;

  for (const entry of corrections) {
    if (entry.action === 'skipped') continue;

    const humanCat = entry.humanVerified;
    const aiCat = entry.aiDetected;

    if (!categoryStats[humanCat]) {
      categoryStats[humanCat] = {
        confirmed: 0,
        corrected: 0,
        confusionSources: {},
        correctedKeywords: [],
        confirmedKeywords: [],
        explicitUserKeywords: new Set<string>(),
      };
    }

    // Process user-typed custom keyword / trigger phrase
    if (entry.customKeyword && entry.customKeyword.trim().length > 1) {
      const kw = entry.customKeyword.trim().toLowerCase();
      categoryStats[humanCat]!.explicitUserKeywords.add(kw);
      
      // Also add individual meaningful words if it's a phrase
      const parts = kw.split(/[,;\/]+/).map(p => p.trim()).filter(p => p.length > 2);
      for (const part of parts) {
        categoryStats[humanCat]!.explicitUserKeywords.add(part);
      }
    }

    if (entry.action === 'confirmed') {
      categoryStats[humanCat]!.confirmed++;
      totalConfirmed++;

      // Track keywords that led to correct classifications
      if (entry.matchedKeywords) {
        categoryStats[humanCat]!.confirmedKeywords.push(...entry.matchedKeywords);
      }
    } else if (entry.action === 'changed') {
      categoryStats[humanCat]!.corrected++;
      totalChanged++;

      // Track confusion: AI thought it was aiCat but human said humanCat
      if (aiCat !== humanCat) {
        categoryStats[humanCat]!.confusionSources[aiCat] =
          (categoryStats[humanCat]!.confusionSources[aiCat] || 0) + 1;

        // The AI's wrong category should suppress the keywords that caused confusion
        if (!categoryStats[aiCat]) {
          categoryStats[aiCat] = {
            confirmed: 0,
            corrected: 0,
            confusionSources: {},
            correctedKeywords: [],
            confirmedKeywords: [],
            explicitUserKeywords: new Set<string>(),
          };
        }

        if (entry.matchedKeywords) {
          categoryStats[aiCat]!.correctedKeywords.push(...entry.matchedKeywords);
        }
      }
    }
  }

  // Generate learned weights
  const categories: Record<string, LearnedCategoryWeight> = {};

  for (const [catId, stats] of Object.entries(categoryStats)) {
    // Find keywords that frequently appear in correct classifications for this category
    const confirmedKeywordFreq: Record<string, number> = {};
    for (const kw of stats.confirmedKeywords) {
      if (kw.startsWith('dir_hint:') || kw.startsWith('pattern:')) continue;
      confirmedKeywordFreq[kw] = (confirmedKeywordFreq[kw] || 0) + 1;
    }

    // Find keywords that led to wrong classifications (should be suppressed for this category)
    const suppressKeywordFreq: Record<string, number> = {};
    for (const kw of stats.correctedKeywords) {
      if (kw.startsWith('dir_hint:') || kw.startsWith('pattern:')) continue;
      suppressKeywordFreq[kw] = (suppressKeywordFreq[kw] || 0) + 1;
    }

    // Start with all explicit human keywords (highest priority, immediate boost)
    const boostKeywordsSet = new Set<string>(stats.explicitUserKeywords);

    // Also boost keywords that appeared in >= 2 correct classifications
    for (const [kw, count] of Object.entries(confirmedKeywordFreq)) {
      if (count >= 2) {
        boostKeywordsSet.add(kw);
      }
    }

    // Suppress keywords that caused >= 2 misclassifications (unless explicitly requested by user)
    const suppress_keywords = Object.entries(suppressKeywordFreq)
      .filter(([kw, count]) => count >= 2 && !boostKeywordsSet.has(kw))
      .sort(([, a], [, b]) => b - a)
      .map(([kw]) => kw);

    // Priority adjustment: categories that are frequently corrected INTO get a boost
    let priority_adjustment = 0;
    if (stats.corrected >= 3) {
      priority_adjustment = Math.min(3, Math.floor(stats.corrected / 3));
    }

    categories[catId] = {
      boost_keywords: Array.from(boostKeywordsSet),
      suppress_keywords,
      priority_adjustment,
      confusion_sources: stats.confusionSources,
      total_confirmed: stats.confirmed,
      total_corrected: stats.corrected,
    };
  }

  const totalActions = totalConfirmed + totalChanged;
  const accuracy = totalActions > 0 ? (totalConfirmed / totalActions) * 100 : 100;

  return {
    generated_at: new Date().toISOString(),
    total_corrections_analysed: corrections.filter((c) => c.action !== 'skipped').length,
    overall_ai_accuracy: Math.round(accuracy * 100) / 100,
    categories,
  };
}

async function retrain() {
  console.log('\n=============================================================');
  console.log('🧠 GoaOnAuto Classifier Retraining Engine');
  console.log('=============================================================\n');

  // 1. Read corrections
  const corrections = readCorrections();
  if (corrections.length === 0) {
    console.log('ℹ️  No corrections found in dataset/corrections.jsonl');
    console.log('👉 Run "bun run harvest-interactive" first to classify documents.\n');
    return;
  }

  const actionable = corrections.filter((c) => c.action !== 'skipped');
  console.log(`📝 Loaded ${corrections.length} total entries (${actionable.length} actionable, ${corrections.length - actionable.length} skipped)`);

  // 2. Count dataset files
  const datasetCounts = countDatasetFiles();
  const totalDatasetFiles = Object.values(datasetCounts).reduce((a, b) => a + b, 0);
  console.log(`📁 Dataset contains ${totalDatasetFiles} files across ${Object.keys(datasetCounts).length} categories\n`);

  // 3. Analyse corrections
  console.log('🔍 Analysing misclassification patterns & user custom keywords...');
  const learnedWeights = analyseCorrections(corrections);

  // 4. Write learned weights
  const weightsPath = path.resolve('./dataset/learned_weights.json');
  fs.writeFileSync(weightsPath, JSON.stringify(learnedWeights, null, 2), 'utf-8');
  console.log(`✅ Learned weights saved to: ${weightsPath}\n`);

  // 5. Print summary
  console.log('=============================================================');
  console.log('📈 RETRAINING SUMMARY');
  console.log('=============================================================');
  console.log(`  🎯 Overall AI Accuracy:    ${learnedWeights.overall_ai_accuracy}%`);
  console.log(`  📊 Total Actions Analysed: ${learnedWeights.total_corrections_analysed}`);
  console.log('');

  // Print per-category details
  const changedCategories = Object.entries(learnedWeights.categories).filter(
    ([, w]) => w.boost_keywords.length > 0 || w.suppress_keywords.length > 0 || w.priority_adjustment > 0
  );

  if (changedCategories.length > 0) {
    console.log('  📚 Learned Adjustments:');
    for (const [catId, weights] of changedCategories) {
      console.log(`\n  ┌─ ${catId}`);
      console.log(`  │  Confirmed: ${weights.total_confirmed} | Corrected Into: ${weights.total_corrected}`);

      if (weights.boost_keywords.length > 0) {
        console.log(`  │  ⬆️  Boost Keywords:    ${weights.boost_keywords.join(', ')}`);
      }
      if (weights.suppress_keywords.length > 0) {
        console.log(`  │  ⬇️  Suppress Keywords: ${weights.suppress_keywords.join(', ')}`);
      }
      if (weights.priority_adjustment > 0) {
        console.log(`  │  🔺 Priority Boost:    +${weights.priority_adjustment}`);
      }
      if (Object.keys(weights.confusion_sources).length > 0) {
        const confusions = Object.entries(weights.confusion_sources)
          .map(([src, count]) => `${src}(${count}x)`)
          .join(', ');
        console.log(`  │  🔀 Confused With:     ${confusions}`);
      }
      console.log(`  └──────────────────────────────────────`);
    }
  } else {
    console.log('  ℹ️  No significant patterns found yet (need more corrections).');
  }

  // Dataset size breakdown
  console.log('\n  📁 Dataset Category Sizes:');
  for (const [cat, count] of Object.entries(datasetCounts).sort(([, a], [, b]) => b - a)) {
    console.log(`     ${cat.padEnd(22)}: ${count} files`);
  }

  console.log('\n=============================================================');
  console.log('✅ Classifier will auto-load learned_weights.json on next run.');
  console.log('=============================================================\n');
}

retrain();
