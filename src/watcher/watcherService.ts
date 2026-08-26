/**
 * File System Watcher Service.
 * Single Responsibility: Listens to file system events and feeds the DirectoryChangeBuffer.
 */
import * as fs from 'fs';
import * as path from 'path';
import { DirectoryChangeBuffer, DirectoryNode } from './directoryBuffer';

export class WatcherService {
  private buffer: DirectoryChangeBuffer;
  private rootPath: string;
  private fsWatcher: fs.FSWatcher | null = null;

  constructor(rootDirectoryPath: string, buffer?: DirectoryChangeBuffer) {
    this.rootPath = path.resolve(rootDirectoryPath);
    this.buffer = buffer || new DirectoryChangeBuffer(this.rootPath);
  }

  public getBuffer(): DirectoryChangeBuffer {
    return this.buffer;
  }

  public start(onDirtyNodesChanged: (dirtyNodes: DirectoryNode[]) => void): void {
    if (this.fsWatcher) return;

    if (!fs.existsSync(this.rootPath)) {
      fs.mkdirSync(this.rootPath, { recursive: true });
    }

    this.fsWatcher = fs.watch(this.rootPath, { recursive: true }, (eventType, filename) => {
      if (!filename) return;
      const fullPath = path.join(this.rootPath, filename);
      const changeType = eventType === 'rename' ? (fs.existsSync(fullPath) ? 'add' : 'unlink') : 'change';

      this.buffer.markChange(fullPath, changeType);
      
      const dirtyNodes = this.buffer.getChangesDFS();
      if (dirtyNodes.length > 0) {
        onDirtyNodesChanged(dirtyNodes);
      }
    });
  }

  public stop(): void {
    if (this.fsWatcher) {
      this.fsWatcher.close();
      this.fsWatcher = null;
    }
  }
}
