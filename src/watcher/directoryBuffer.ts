/**
 * Trie-Based Directory Change Buffer.
 * Single Responsibility: Tracks file additions across nested folders with dirty-bit propagation and DFS traversal.
 */
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

  constructor(rootDirectoryPath: string) {
    this.rootPath = path.resolve(rootDirectoryPath);
    this.root = new DirectoryNode(path.basename(this.rootPath) || this.rootPath, this.rootPath);
  }

  public markChange(targetFilePath: string, eventType: 'add' | 'change' | 'unlink' = 'add'): void {
    const absoluteFilePath = path.resolve(targetFilePath);
    
    if (!absoluteFilePath.startsWith(this.rootPath)) {
      return;
    }

    const relativePath = path.relative(this.rootPath, absoluteFilePath);
    if (!relativePath) return;

    const parts = relativePath.split(path.sep);
    const fileName = parts.pop()!;

    let currentNode = this.root;
    let currentPath = this.rootPath;

    for (const dirName of parts) {
      if (!dirName || dirName === '.') continue;
      currentPath = path.join(currentPath, dirName);

      if (!currentNode.children.has(dirName)) {
        const newNode = new DirectoryNode(dirName, currentPath, currentNode);
        currentNode.children.set(dirName, newNode);
      }
      currentNode = currentNode.children.get(dirName)!;
    }

    currentNode.hasDirectChanges = true;
    currentNode.changedFiles.set(fileName, {
      filePath: absoluteFilePath,
      eventType,
      timestamp: Date.now()
    });
    
    currentNode.setDirty();
  }

  public getChangesDFS(node: DirectoryNode = this.root): DirectoryNode[] {
    if (!node.isDirty) {
      return [];
    }

    const changedNodes: DirectoryNode[] = [];

    if (node.hasDirectChanges) {
      changedNodes.push(node);
    }

    for (const child of node.children.values()) {
      if (child.isDirty) {
        changedNodes.push(...this.getChangesDFS(child));
      }
    }

    return changedNodes;
  }

  public resetBuffer(): void {
    this.root.clearDirty();
  }
}
