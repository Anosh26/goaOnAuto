import { describe, it, expect, beforeAll, afterAll } from "bun:test";
import * as fs from "fs";
import * as path from "path";
import { spawnSync } from "child_process";

const BIN_DIR = path.join(__dirname, "../bin");
const EXE_PATH = path.join(BIN_DIR, "process_image.exe");
const TEMP_DIR = path.join(__dirname, "temp");

// Helper to parse JPEG dimensions without external libraries
function getJpegDimensions(filePath: string): { width: number; height: number } {
  const buffer = fs.readFileSync(filePath);
  let i = 2; // Skip SOI (0xFFD8)
  while (i < buffer.length) {
    if (buffer[i] === 0xff) {
      const marker = buffer[i + 1];
      if (marker === 0xc0 || marker === 0xc2) {
        // SOF0 (Baseline DCT) or SOF2 (Progressive DCT)
        const height = buffer.readUInt16BE(i + 5);
        const width = buffer.readUInt16BE(i + 7);
        return { width, height };
      }
      // Skip this marker
      const length = buffer.readUInt16BE(i + 2);
      i += 2 + length;
    } else {
      i++;
    }
  }
  throw new Error("SOF marker not found in JPEG");
}

// Helper to generate a 24-bit uncompressed BMP image programmatically
function generateMockBMP(width: number, height: number, filePath: string) {
  const rowSize = Math.floor((24 * width + 31) / 32) * 4;
  const pixelDataSize = rowSize * height;
  const fileSize = 54 + pixelDataSize;

  const buffer = Buffer.alloc(fileSize);

  // BMP Header
  buffer.write("BM", 0, 2, "ascii");
  buffer.writeUInt32LE(fileSize, 2);
  buffer.writeUInt32LE(0, 6);
  buffer.writeUInt32LE(54, 10);

  // DIB Header
  buffer.writeUInt32LE(40, 14);
  buffer.writeInt32LE(width, 18);
  buffer.writeInt32LE(height, 22);
  buffer.writeUInt16LE(1, 26);
  buffer.writeUInt16LE(24, 28);
  buffer.writeUInt32LE(0, 30); // No compression
  buffer.writeUInt32LE(pixelDataSize, 34);
  buffer.writeInt32LE(2835, 38);
  buffer.writeInt32LE(2835, 42);
  buffer.writeUInt32LE(0, 46);
  buffer.writeUInt32LE(0, 50);

  // Fill pixels: background is light grey, foreground (center circle) is dark
  const bgB = 220, bgG = 220, bgR = 220; // light grey background
  const fgB = 100, fgG = 50, fgR = 30;   // dark center color
  
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) / 4;

  let offset = 54;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const dx = x - cx;
      const dy = y - cy;
      const insideCenter = (dx * dx + dy * dy < radius * radius);
      
      const pixelOffset = offset + x * 3;
      if (insideCenter) {
        buffer.writeUInt8(fgB, pixelOffset);
        buffer.writeUInt8(fgG, pixelOffset + 1);
        buffer.writeUInt8(fgR, pixelOffset + 2);
      } else {
        buffer.writeUInt8(bgB, pixelOffset);
        buffer.writeUInt8(bgG, pixelOffset + 1);
        buffer.writeUInt8(bgR, pixelOffset + 2);
      }
    }
    // Row padding
    for (let p = width * 3; p < rowSize; p++) {
      buffer.writeUInt8(0, offset + p);
    }
    offset += rowSize;
  }

  fs.writeFileSync(filePath, buffer);
}

describe("Image Processor Module", () => {
  const inputBmp = path.join(TEMP_DIR, "test_input.bmp");
  const outputJpg = path.join(TEMP_DIR, "test_output.jpg");
  const customJpg = path.join(TEMP_DIR, "test_custom.jpg");

  beforeAll(() => {
    // Ensure clean directories
    if (!fs.existsSync(BIN_DIR)) {
      fs.mkdirSync(BIN_DIR, { recursive: true });
    }
    if (!fs.existsSync(TEMP_DIR)) {
      fs.mkdirSync(TEMP_DIR, { recursive: true });
    }
    
    // Compile binary
    console.log("Compiling image_processor.c...");
    const srcPath = path.join(__dirname, "../src/image_processor/image_processor.c");
    const compileResult = spawnSync("gcc", ["-O3", "-o", EXE_PATH, srcPath, "-lm"], { shell: true });
    
    if (compileResult.status !== 0) {
      console.error(compileResult.stderr.toString());
      throw new Error("Compilation of image_processor.c failed!");
    }
    
    // Generate mock input BMP (400x400)
    generateMockBMP(400, 400, inputBmp);
  }, 30000);

  afterAll(() => {
    // Clean up temporary test files
    try {
      if (fs.existsSync(inputBmp)) fs.unlinkSync(inputBmp);
      if (fs.existsSync(outputJpg)) fs.unlinkSync(outputJpg);
      if (fs.existsSync(customJpg)) fs.unlinkSync(customJpg);
      if (fs.existsSync(TEMP_DIR)) fs.rmdirSync(TEMP_DIR);
    } catch (e) {
      console.warn("Cleanup warning:", e);
    }
  });

  it("should compile successfully and create the executable", () => {
    expect(fs.existsSync(EXE_PATH)).toBe(true);
  });

  it("should run with default parameters (50% scale, compression < 50KB)", () => {
    const runResult = spawnSync(EXE_PATH, [inputBmp, outputJpg], { shell: true });
    expect(runResult.status).toBe(0);
    expect(fs.existsSync(outputJpg)).toBe(true);
    
    // Check file size is strictly under 50 KB (51200 bytes)
    const stats = fs.statSync(outputJpg);
    expect(stats.size).toBeLessThan(51200);
    
    // Check dimensions (400x400 scaled by 50% = 200x200)
    const dims = getJpegDimensions(outputJpg);
    expect(dims.width).toBe(200);
    expect(dims.height).toBe(200);
  });

  it("should support custom target dimensions", () => {
    const runResult = spawnSync(EXE_PATH, ["--width", "120", "--height", "180", inputBmp, customJpg], { shell: true });
    expect(runResult.status).toBe(0);
    expect(fs.existsSync(customJpg)).toBe(true);
    
    // Check custom dimensions are exactly as requested
    const dims = getJpegDimensions(customJpg);
    expect(dims.width).toBe(120);
    expect(dims.height).toBe(180);
    
    // Check file size is strictly under 50 KB
    const stats = fs.statSync(customJpg);
    expect(stats.size).toBeLessThan(51200);
  });

  it("should correctly identify background and change top corners to pure white", () => {
    // Run process_image with --verify-pixel to check top-left (0,0) and top-right (199, 0)
    const verifyLeft = spawnSync(EXE_PATH, ["--verify-pixel", "0", "0", inputBmp, outputJpg], { shell: true });
    expect(verifyLeft.status).toBe(0);
    const outputL = verifyLeft.stdout.toString();
    expect(outputL).toContain("VERIFY_PIXEL: R=255, G=255, B=255");
    
    const verifyRight = spawnSync(EXE_PATH, ["--verify-pixel", "199", "0", inputBmp, outputJpg], { shell: true });
    expect(verifyRight.status).toBe(0);
    const outputR = verifyRight.stdout.toString();
    expect(outputR).toContain("VERIFY_PIXEL: R=255, G=255, B=255");
  });

  it("should NOT clear the center subject pixels to white", () => {
    // Center is (100, 100) on 200x200 resized image.
    // Check that it stays at original/foreground colors (approx R=30, G=50, B=100) and NOT 255.
    const verifyCenter = spawnSync(EXE_PATH, ["--verify-pixel", "100", "100", inputBmp, outputJpg], { shell: true });
    expect(verifyCenter.status).toBe(0);
    const output = verifyCenter.stdout.toString();
    expect(output).toContain("VERIFY_PIXEL:");
    expect(output).not.toContain("R=255, G=255, B=255");
  });

  it("should respect custom --max-kb target file size limit", () => {
    const customKbJpg = path.join(TEMP_DIR, "test_custom_kb.jpg");
    const runResult = spawnSync(EXE_PATH, ["--max-kb", "15", inputBmp, customKbJpg], { shell: true });
    expect(runResult.status).toBe(0);
    expect(fs.existsSync(customKbJpg)).toBe(true);
    
    const stats = fs.statSync(customKbJpg);
    expect(stats.size).toBeLessThanOrEqual(15 * 1024);
    if (fs.existsSync(customKbJpg)) fs.unlinkSync(customKbJpg);
  });

  it("should support --skip-bg-remove flag when AI pre-processing is used", () => {
    const skipBgJpg = path.join(TEMP_DIR, "test_skip_bg.jpg");
    const runResult = spawnSync(EXE_PATH, ["--skip-bg-remove", inputBmp, skipBgJpg], { shell: true });
    expect(runResult.status).toBe(0);
    expect(fs.existsSync(skipBgJpg)).toBe(true);
    const output = runResult.stdout.toString();
    expect(output).toContain("Skipping C flood-fill background removal");
    if (fs.existsSync(skipBgJpg)) fs.unlinkSync(skipBgJpg);
  });
});
