import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { createBaseXORPool } from '@basexor/shared';
import { createServerDB } from './db';
import * as path from 'path';

const PORT = process.env.SERVER_PORT || 3001;
const API_TOKEN = process.env.API_TOKEN || 'baseXOR_jmk_api_token_2026';
const PROXY_TARGET = process.env.PROXY_TARGET || 'http://127.0.0.1:80';
const UPLOAD_DIR = path.join(__dirname, '../uploads');

const app = express();
const xorPool = createBaseXORPool(API_TOKEN);
const serverDB = createServerDB(UPLOAD_DIR);

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, serverDB.getUploadDir());
  },
  filename: (req, file, cb) => {
    const uniqueName = `${Date.now()}-${file.originalname}`;
    cb(null, uniqueName);
  },
});

const upload = multer({ storage });

app.use(cors());
app.use(express.json());

const xorAuthMiddleware = (req: express.Request, res: express.Response, next: express.NextFunction) => {
  const authHeader = req.headers['x-jmk-auth'] as string;
  if (!authHeader) {
    return res.status(403).json({ code: 403, msg: 'Proxy Auth Failed' });
  }

  const verifyResult = xorPool.verifyTag(authHeader);
  if (!verifyResult.valid) {
    return res.status(403).json({ code: 403, msg: 'Proxy Auth Failed' });
  }

  (req as any).tagInfo = verifyResult;
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
    .then(r => r.json() as Promise<{ valid: boolean; tag_auth?: string; expire_at?: number; msg?: string }>)
    .then(data => {
      if (data.valid && data.tag_auth && data.expire_at) {
        serverDB.activateTag('theme_premium', data.tag_auth, data.expire_at);
        res.json({
          code: 0,
          msg: 'tag activated successfully',
          tag_id: 'theme_premium',
          expire_at: data.expire_at,
        });
      } else {
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

  const resource = serverDB.addResource(
    tagId,
    file.originalname,
    file.path,
    file.size
  );

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

app.use('/proxy', xorAuthMiddleware, createProxyMiddleware({
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
