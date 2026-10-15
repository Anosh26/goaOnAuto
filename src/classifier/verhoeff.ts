/**
 * Verhoeff Modulo-10 Dihedral Checksum Algorithm (D5 Group).
 * Single Responsibility: Validates 12-digit Indian Aadhaar numbers against transposition and single-digit errors.
 */

// Dihedral D5 multiplication table
const d: number[][] = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
  [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
  [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
  [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
  [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
  [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
];

// Permutation table p
const p: number[][] = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
  [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
  [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
  [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
  [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
];

// Inversion table
const inv: number[] = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9];

/**
 * Validates a numeric string (such as an Aadhaar number) using the Verhoeff algorithm.
 *
 * @param numStr - Numeric string (e.g. "999999990019")
 * @returns true if the checksum evaluates to 0, false otherwise.
 */
export function validateVerhoeff(numStr: string): boolean {
  const clean = numStr.replace(/\D/g, '');
  if (!clean || clean.length < 2) return false;

  let c = 0;
  const digits = clean.split('').map(Number).reverse();

  for (let i = 0; i < digits.length; i++) {
    c = d[c][p[i % 8][digits[i]]];
  }

  return c === 0;
}

/**
 * Calculates the Verhoeff check digit for an input string.
 *
 * @param numStr - Base number string without check digit
 * @returns The check digit (0-9)
 */
export function generateVerhoeffCheckDigit(numStr: string): number {
  const clean = numStr.replace(/\D/g, '');
  let c = 0;
  const digits = clean.split('').map(Number).reverse();

  for (let i = 0; i < digits.length; i++) {
    c = d[c][p[(i + 1) % 8][digits[i]]];
  }

  return inv[c];
}
