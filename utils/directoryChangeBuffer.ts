import * as fs from 'fs';
import * as path from 'path';

export interface ChangedFileRecord {
  filePath: string;
  eventType: 'add' | 'change' | 'unlink';
  timestamp: number;
}

export class DirectoryNode {
  public name: string;
  public fullPath: string;
  public isDirty: boolean = false;
  public hasDirectChanges: boolean = false;
  public children: Map<string, DirectoryNode> = new Map();
  public changedFiles: Map<string, ChangedFileRecord> = new Map();
  public parent: DirectoryNode | null = null;

  constructor(name: string, fullPath: string, parent: DirectoryNode | null = null) {
    this.name = name;
    this.fullPath = fullPath;
    this.parent = parent;
  }

  public setDirty(): void {
    let current: DirectoryNode | null = this;
    while (current) {
      current.isDirty = true;
      current = current.parent;
    }
  }

  public clearDirty(): void {
    this.isDirty = false;
    this.hasDirectChanges = false;
    this.changedFiles.clear();
    for (const child of this.children.values()) {
      child.clearDirty();
    }
  }
}

export class DirectoryChangeBuffer {
  public root: DirectoryNode;
  private rootPath: string;
  private fsWatcher: fs.FSWatcher | null = null;

  constructor(rootDirectoryPath: string) {
    this.rootPath = path.resolve(rootDirectoryPath);
    this.root = new DirectoryNode(path.basename(this.rootPath) || this.rootPath, this.rootPath);
  }

  /**
   * Mark a file change in the tree buffer and propagate dirty bit to root
   */
  public markChange(targetFilePath: string, eventType: 'add' | 'change' | 'unlink' = 'add'): void {
    const absoluteFilePath = path.resolve(targetFilePath);
    
    // Ensure file is within root directory tree
    if (!absoluteFilePath.startsWith(this.rootPath)) {
      return;
    }

    const relativePath = path.relative(this.rootPath, absoluteFilePath);
    if (!relativePath) return;

    const parts = relativePath.split(path.sep);
    const fileName = parts.pop()!;

    let currentNode = this.root;
    let currentPath = this.rootPath;

    // Build/traverse directory tree nodes down to target directory
    for (const dirName of parts) {
      if (!dirName || dirName === '.') continue;
      currentPath = path.join(currentPath, dirName);

      if (!currentNode.children.has(dirName)) {
        const newNode = new DirectoryNode(dirName, currentPath, currentNode);
        currentNode.children.set(dirName, newNode);
      }
      currentNode = currentNode.children.get(dirName)!;
    }

    // Record change and turn ON dirty bit up to root
    currentNode.hasDirectChanges = true;
    currentNode.changedFiles.set(fileName, {
      filePath: absoluteFilePath,
      eventType,
      timestamp: Date.now()
    });
    
    currentNode.setDirty();
  }

  /**
   * Depth-First Search (DFS) traversal to find all changed directories/files
   */
  public getChangesDFS(node: DirectoryNode = this.root): DirectoryNode[] {
    // If bit is 0, no changes in this branch, skip entirely
    if (!node.isDirty) {
      return [];
    }

    const changedNodes: DirectoryNode[] = [];

    // If this node has direct file changes, collect it first
    if (node.hasDirectChanges) {
      changedNodes.push(node);
    }

    // Recurse depth-first into dirty children
    for (const child of node.children.values()) {
      if (child.isDirty) {
        changedNodes.push(...this.getChangesDFS(child));
      }
    }

    return changedNodes;
  }

  /**
   * Reset dirty bits across the tree
   */
  public resetBuffer(): void {
    this.root.clearDirty();
  }

  /**
   * Start active file system watcher on the directory path
   */
  public startWatching(onBufferUpdated?: (dirtyNodes: DirectoryNode[]) => void): void {
    if (this.fsWatcher) return;

    if (!fs.existsSync(this.rootPath)) {
      fs.mkdirSync(this.rootPath, { recursive: true });
    }

    this.fsWatcher = fs.watch(this.rootPath, { recursive: true }, (eventType, filename) => {
      if (!filename) return;
      const fullPath = path.join(this.rootPath, filename);
      const changeType = eventType === 'rename' ? (fs.existsSync(fullPath) ? 'add' : 'unlink') : 'change';

      this.markChange(fullPath, changeType);
      
      if (onBufferUpdated) {
        onBufferUpdated(this.getChangesDFS());
      }
    });
  }

  /**
   * Stop active file system watcher
   */
  public stopWatching(): void {
    if (this.fsWatcher) {
      this.fsWatcher.close();
      this.fsWatcher = null;
    }
  }
}
