import * as fs from 'fs';
import * as path from 'path';
import { DirectoryChangeBuffer } from '../src/watcher/directoryBuffer';
import { processDocumentImage } from '../src/scanner/documentScanner';

const testWorkDir = path.resolve('./tests/mock_work_dir');

// Setup mock subdirectories: residence, pcc, caste_certificate, obc
const subDirs = ['residence', 'pcc', 'caste_certificate', 'obc'];
subDirs.forEach(sub => fs.mkdirSync(path.join(testWorkDir, sub), { recursive: true }));

console.log('=== Testing Work Directory Watcher Simulation ===');
console.log(`📁 Mock Root Work Dir: ${testWorkDir}`);

const buffer = new DirectoryChangeBuffer(testWorkDir);

// 1. Simulate dropping a Police Clearance Certificate (PCC) inside mock_work_dir/pcc/
const samplePCCPath = path.join(testWorkDir, 'pcc', 'scan_102.jpg');
console.log(`\n📥 [Simulated Change] Adding new document at dynamic path: ${samplePCCPath}`);

// Mark buffer change
buffer.markChange(samplePCCPath, 'add');

// 2. Perform DFS traversal
const dirtyNodes = buffer.getChangesDFS();
console.log(`🔍 [DFS Traversal] Found ${dirtyNodes.length} dirty nodes:`);

dirtyNodes.forEach(node => {
  console.log(`   📂 Path: ${node.fullPath} (Dirty Bit = ${node.isDirty ? 1 : 0})`);
  console.log(`   📄 Files: ${Array.from(node.changedFiles.keys()).join(', ')}`);
});

// Clean up mock directory
fs.rmSync(testWorkDir, { recursive: true, force: true });
console.log('\n✅ Work directory change detection test passed!');
