import { describe, expect, test } from 'bun:test';
import { validateVerhoeff, generateVerhoeffCheckDigit } from '../src/classifier/verhoeff';

describe('Verhoeff Checksum Algorithm (D5 Group)', () => {
  // 999999990019 is a known mathematically valid Verhoeff 12-digit UID
  const validUid = '999999990019';

  test('should validate a correct 12-digit Aadhaar number', () => {
    expect(validateVerhoeff(validUid)).toBe(true);
  });

  test('should detect single-digit transcription errors', () => {
    // Alter single digit from '9' to '8'
    const corrupted = '999999990018';
    expect(validateVerhoeff(corrupted)).toBe(false);
  });

  test('should detect adjacent transposition errors', () => {
    // Swap adjacent digits '01' to '10'
    const transposed = '999999990109';
    expect(validateVerhoeff(transposed)).toBe(false);
  });

  test('should reject malformed or short numeric inputs', () => {
    expect(validateVerhoeff('')).toBe(false);
    expect(validateVerhoeff('5')).toBe(false);
  });

  test('should generate the correct check digit for a base number', () => {
    const base = '99999999001';
    const checkDigit = generateVerhoeffCheckDigit(base);
    expect(checkDigit).toBe(9);
    expect(validateVerhoeff(base + checkDigit)).toBe(true);
  });
});
