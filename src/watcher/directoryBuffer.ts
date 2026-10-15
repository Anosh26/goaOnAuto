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

  /**
   * Initializes a DirectoryNode within the directory trie.
   *
   * @param name - The directory base folder name.
   * @param fullPath - The absolute filesystem path of the directory.
   * @param parent - The parent DirectoryNode in the trie, or null if root.
   */
  constructor(name: string, fullPath: string, parent: DirectoryNode | null = null) {
    this.name = name;
    this.fullPath = fullPath;
    this.parent = parent;
  }

  /**
   * Sets the dirty state flag on this directory node and bubbles it up
   * through all ancestor nodes up to the trie root.
   */
  public setDirty(): void {
    let current: DirectoryNode | null = this;
    while (current) {
      current.isDirty = true;
      current = current.parent;
    }
  }

  /**
   * Recursively resets the dirty state, clearing direct change indicators,
   * recorded changed file maps, and resetting all child nodes.
   */
  public clearDirty(): void {
    this.isDirty = false;
    this.hasDirectChanges = false;
    this.changedFiles.clear();
    for (const child of this.children.values()) {
      child.clearDirty();
    }
  }
}

/**
 * Trie-based directory change accumulator that tracks file mutations
 * across deeply nested applicant client folders.
 */
export class DirectoryChangeBuffer {
  public root: DirectoryNode;
  private rootPath: string;

  /**
   * Creates a new DirectoryChangeBuffer rooted at the specified filesystem path.
   *
   * @param rootDirectoryPath - The root directory monitored by the watcher.
   */
  constructor(rootDirectoryPath: string) {
    this.rootPath = path.resolve(rootDirectoryPath);
    this.root = new DirectoryNode(path.basename(this.rootPath) || this.rootPath, this.rootPath);
  }

  /**
   * Records a filesystem change for a target file, creating intermediate trie nodes
   * as needed, registering the file mutation, and propagating the dirty flag up to root.
   *
   * @param targetFilePath - Absolute or relative path to the modified file.
   * @param eventType - Nature of the change: 'add', 'change', or 'unlink'. Defaults to 'add'.
   */
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

  /**
   * Traverses the trie via Depth-First Search (DFS) and collects all dirty directory
   * nodes that contain direct file changes ready for batch processing.
   *
   * @param node - The starting node for traversal (defaults to the trie root).
   * @returns An array of DirectoryNode instances containing changed files.
   */
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

  /**
   * Resets the entire trie buffer by recursively clearing dirty flags and changed file maps.
   */
  public resetBuffer(): void {
    this.root.clearDirty();
  }
}
