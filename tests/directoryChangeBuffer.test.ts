import { DirectoryChangeBuffer } from '../utils/directoryChangeBuffer';
import * as path from 'path';

console.log("=== Testing Directory Change Buffer (Dirty Bit Propagation & DFS) ===");

const rootDir = path.resolve('./sample_watch_dir');
const buffer = new DirectoryChangeBuffer(rootDir);

// 1. Initial State: root dirty bit is false (0)
console.log(`Root initial dirty bit: ${buffer.root.isDirty ? 1 : 0}`);

// 2. Simulate change in subfolder dir1/subdirA/file1.txt
const file1 = path.join(rootDir, 'dir1', 'subdirA', 'file1.txt');
console.log(`\n--> Simulating file addition: ${file1}`);
buffer.markChange(file1, 'add');

console.log(`Root dirty bit after change: ${buffer.root.isDirty ? 1 : 0}`);

// 3. Simulate another change in dir2/file2.pdf
const file2 = path.join(rootDir, 'dir2', 'file2.pdf');
console.log(`--> Simulating file addition: ${file2}`);
buffer.markChange(file2, 'add');

// 4. Perform Depth-First Traversal (DFS) to inspect changed directories
console.log("\n--- Performing Depth-First Traversal (DFS) for Dirty Nodes ---");
const changedNodes = buffer.getChangesDFS();

changedNodes.forEach((node, index) => {
  console.log(`[Node ${index + 1}] Directory: ${path.relative(rootDir, node.fullPath) || '.'}`);
  console.log(`          Dirty Bit: ${node.isDirty ? 1 : 0}`);
  console.log(`          Direct Files Changed: ${Array.from(node.changedFiles.keys()).join(', ')}`);
});

// 5. Reset Buffer
console.log("\n--> Resetting buffer...");
buffer.resetBuffer();
console.log(`Root dirty bit after reset: ${buffer.root.isDirty ? 1 : 0}`);
console.log(`DFS nodes after reset: ${buffer.getChangesDFS().length}`);
