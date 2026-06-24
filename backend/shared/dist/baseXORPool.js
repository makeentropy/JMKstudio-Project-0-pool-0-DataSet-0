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
exports.createBaseXORPool = exports.BaseXORPool = void 0;
const crypto = __importStar(require("crypto"));
class BaseXORPool {
    constructor(apiToken) {
        this.apiToken = apiToken;
    }
    xorCrypt(data, key) {
        const dataBytes = Buffer.from(data, 'utf-8');
        const keyBytes = Buffer.from(key, 'utf-8');
        const result = Buffer.alloc(dataBytes.length);
        for (let i = 0; i < dataBytes.length; i++) {
            result[i] = dataBytes[i] ^ keyBytes[i % keyBytes.length];
        }
        return result.toString('base64');
    }
    xorDecrypt(encrypted, key) {
        const dataBytes = Buffer.from(encrypted, 'base64');
        const keyBytes = Buffer.from(key, 'utf-8');
        const result = Buffer.alloc(dataBytes.length);
        for (let i = 0; i < dataBytes.length; i++) {
            result[i] = dataBytes[i] ^ keyBytes[i % keyBytes.length];
        }
        return result.toString('utf-8');
    }
    signTag(tagId, expireTs) {
        const rawPayload = `${tagId}|${expireTs}|${this.apiToken}`;
        return this.xorCrypt(rawPayload, this.apiToken);
    }
    verifyTag(signedStr) {
        try {
            const raw = this.xorDecrypt(signedStr, this.apiToken);
            const parts = raw.split('|');
            if (parts.length !== 3) {
                return { valid: false, tagId: '', expire: 0 };
            }
            const [tagId, expireStr, token] = parts;
            const expire = parseInt(expireStr, 10);
            if (token === this.apiToken && Date.now() / 1000 < expire) {
                return { valid: true, tagId, expire };
            }
            return { valid: false, tagId: '', expire: 0 };
        }
        catch {
            return { valid: false, tagId: '', expire: 0 };
        }
    }
    genRandomStr(length) {
        return crypto.randomBytes(Math.ceil(length / 2)).toString('hex').slice(0, length);
    }
    genUuid() {
        return crypto.randomUUID();
    }
    timestamp() {
        return Math.floor(Date.now() / 1000);
    }
}
exports.BaseXORPool = BaseXORPool;
const createBaseXORPool = (apiToken) => {
    return new BaseXORPool(apiToken);
};
exports.createBaseXORPool = createBaseXORPool;
