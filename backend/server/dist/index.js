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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const multer_1 = __importDefault(require("multer"));
const http_proxy_middleware_1 = require("http-proxy-middleware");
const shared_1 = require("@basexor/shared");
const db_1 = require("./db");
const path = __importStar(require("path"));
const PORT = process.env.SERVER_PORT || 3001;
const API_TOKEN = process.env.API_TOKEN || 'baseXOR_jmk_api_token_2026';
const PROXY_TARGET = process.env.PROXY_TARGET || 'http://127.0.0.1:80';
const UPLOAD_DIR = path.join(__dirname, '../uploads');
const app = (0, express_1.default)();
const xorPool = (0, shared_1.createBaseXORPool)(API_TOKEN);
const serverDB = (0, db_1.createServerDB)(UPLOAD_DIR);
const storage = multer_1.default.diskStorage({
    destination: (req, file, cb) => {
        cb(null, serverDB.getUploadDir());
    },
    filename: (req, file, cb) => {
        const uniqueName = `${Date.now()}-${file.originalname}`;
        cb(null, uniqueName);
    },
});
const upload = (0, multer_1.default)({ storage });
app.use((0, cors_1.default)());
app.use(express_1.default.json());
const xorAuthMiddleware = (req, res, next) => {
    const authHeader = req.headers['x-jmk-auth'];
    if (!authHeader) {
        return res.status(403).json({ code: 403, msg: 'Proxy Auth Failed' });
    }
    const verifyResult = xorPool.verifyTag(authHeader);
    if (!verifyResult.valid) {
        return res.status(403).json({ code: 403, msg: 'Proxy Auth Failed' });
    }
    req.tagInfo = verifyResult;
    next();
};
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        service: 'server.bin',
        timestamp: xorPool.timestamp(),
        tag: 'free_proxy_forward',
    });
});
app.post('/tag/active', (req, res) => {
    const { card_key } = req.body;
    if (!card_key) {
        return res.status(400).json({ code: 400, msg: 'card_key required' });
    }
    fetch(`http://localhost:3002/card/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_key }),
    })
        .then(r => r.json())
        .then(data => {
        if (data.valid && data.tag_auth && data.expire_at) {
            serverDB.activateTag('theme_premium', data.tag_auth, data.expire_at);
            res.json({
                code: 0,
                msg: 'tag activated successfully',
                tag_id: 'theme_premium',
                expire_at: data.expire_at,
            });
        }
        else {
            res.status(400).json({ code: 400, msg: data.msg || 'activation failed' });
        }
    })
        .catch(() => {
        res.status(500).json({ code: 500, msg: 'server error' });
    });
});
app.post('/tag/resource/upload', xorAuthMiddleware, upload.single('resource'), (req, res) => {
    const tagId = req.body.tag_id;
    const file = req.file;
    if (!file) {
        return res.status(400).json({ code: 400, msg: 'no file uploaded' });
    }
    const resource = serverDB.addResource(tagId, file.originalname, file.path, file.size);
    res.json({
        code: 0,
        msg: 'upload success',
        resource,
    });
});
app.get('/tag/resources/:tagId', xorAuthMiddleware, (req, res) => {
    const tagId = req.params.tagId;
    const resources = serverDB.getResources(tagId);
    res.json({ code: 0, resources });
});
app.get('/proxy/health', (req, res) => {
    res.json({
        status: 'alive',
        proxy_target: PROXY_TARGET,
        tag: 'free_proxy_forward',
    });
});
app.use('/proxy', xorAuthMiddleware, (0, http_proxy_middleware_1.createProxyMiddleware)({
    target: PROXY_TARGET,
    changeOrigin: true,
    pathRewrite: {
        '^/proxy': '',
    },
    onProxyReq: (proxyReq, req, res) => {
        console.log(`[PROXY] Forwarding to ${PROXY_TARGET}${req.url}`);
    },
}));
app.listen(PORT, () => {
    console.log(`[INFO] server.bin started on port ${PORT}`);
    console.log(`[INFO] BaseXOR pool initialized`);
    console.log(`[INFO] Free proxy tag: free_proxy_forward`);
    console.log(`[INFO] Proxy target: ${PROXY_TARGET}`);
});
