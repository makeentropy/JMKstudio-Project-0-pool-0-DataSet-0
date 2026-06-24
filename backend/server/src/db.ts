import * as fs from 'fs';
import * as path from 'path';

export interface TagResource {
  tag_id: string;
  file_name: string;
  file_path: string;
  size: number;
  uploaded_at: number;
}

export interface ActiveTag {
  tag_id: string;
  auth_sign: string;
  activated_at: number;
  expire_at: number;
}

export class ServerDB {
  private activeTags: Map<string, ActiveTag> = new Map();
  private resources: Map<string, TagResource[]> = new Map();
  private uploadDir: string;

  constructor(uploadDir: string) {
    this.uploadDir = uploadDir;
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
  }

  activateTag(tagId: string, authSign: string, expireAt: number): ActiveTag {
    const tag: ActiveTag = {
      tag_id: tagId,
      auth_sign: authSign,
      activated_at: Math.floor(Date.now() / 1000),
      expire_at: expireAt,
    };
    this.activeTags.set(tagId, tag);
    return tag;
  }

  getActiveTag(tagId: string): ActiveTag | undefined {
    return this.activeTags.get(tagId);
  }

  isTagActive(tagId: string): boolean {
    const tag = this.activeTags.get(tagId);
    if (!tag) return false;
    return Math.floor(Date.now() / 1000) < tag.expire_at;
  }

  addResource(tagId: string, fileName: string, filePath: string, size: number): TagResource {
    const resource: TagResource = {
      tag_id: tagId,
      file_name: fileName,
      file_path: filePath,
      size: size,
      uploaded_at: Math.floor(Date.now() / 1000),
    };

    if (!this.resources.has(tagId)) {
      this.resources.set(tagId, []);
    }
    this.resources.get(tagId)!.push(resource);
    return resource;
  }

  getResources(tagId: string): TagResource[] {
    return this.resources.get(tagId) || [];
  }

  getUploadDir(): string {
    return this.uploadDir;
  }
}

export const createServerDB = (uploadDir: string) => {
  return new ServerDB(uploadDir);
};
