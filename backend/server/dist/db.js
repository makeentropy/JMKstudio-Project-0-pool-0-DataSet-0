"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.createServerDB = exports.ServerDB = void 0;
const fs = __importStar(require("fs"));
class ServerDB {
    constructor(uploadDir) {
        this.activeTags = new Map();
        this.resources = new Map();
        this.uploadDir = uploadDir;
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir, { recursive: true });
        }
    }
    activateTag(tagId, authSign, expireAt) {
        const tag = {
            tag_id: tagId,
            auth_sign: authSign,
            activated_at: Math.floor(Date.now() / 1000),
            expire_at: expireAt,
        };
        this.activeTags.set(tagId, tag);
        return tag;
    }
    getActiveTag(tagId) {
        return this.activeTags.get(tagId);
    }
    isTagActive(tagId) {
        const tag = this.activeTags.get(tagId);
        if (!tag)
            return false;
        return Math.floor(Date.now() / 1000) < tag.expire_at;
    }
    addResource(tagId, fileName, filePath, size) {
        const resource = {
            tag_id: tagId,
            file_name: fileName,
            file_path: filePath,
            size: size,
            uploaded_at: Math.floor(Date.now() / 1000),
        };
        if (!this.resources.has(tagId)) {
            this.resources.set(tagId, []);
        }
        this.resources.get(tagId).push(resource);
        return resource;
    }
    getResources(tagId) {
        return this.resources.get(tagId) || [];
    }
    getUploadDir() {
        return this.uploadDir;
    }
}
exports.ServerDB = ServerDB;
const createServerDB = (uploadDir) => {
    return new ServerDB(uploadDir);
};
exports.createServerDB = createServerDB;
