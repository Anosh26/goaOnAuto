/**
 * Integration Test for Raylib Human Confirmation GUI.
 */
import { describe, test, expect } from 'bun:test';
import * as path from 'path';
import * as fs from 'fs';
import { requestHumanConfirmation } from '../src/gui/confirmationBridge';
import { config } from '../src/config';

describe('Raylib Human Confirmation GUI System', () => {
  test('should initialize confirmation bridge with config settings', () => {
    expect(typeof config.enableHumanConfirmation).toBe('boolean');
    expect(config.minFreeRamBytes).toBe(3 * 1024 * 1024 * 1024);
    expect(config.maxCpuPercent).toBe(80);
    expect(config.maxGpuMemoryFraction).toBe(0.9);
  });

  test('should return error when target file does not exist', async () => {
    const res = await requestHumanConfirmation({
      filePath: path.join(config.projectRoot, 'non_existent_file.jpg'),
      docType: 'aadhaar',
      docTypeName: 'Aadhaar Card',
      extractedName: 'Rahul Sharma',
      confidence: 0.95
    });

    expect(res.action).toBe('error');
  });
});
