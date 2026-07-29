import path from 'path';
import fs from 'fs';
import { Express, Request, Response, NextFunction } from 'express';
import logger from '../utils/logger';

const NONCE_PLACEHOLDER = '__CSP_NONCE_PLACEHOLDER__';
const FRONTEND_DIR_NAME = 'frontend';
const INDEX_HTML_NAME = 'index.html';

export function serveFrontend(app: Express): void {
  const projectRoot = process.cwd();
  const frontendDir = path.resolve(projectRoot, FRONTEND_DIR_NAME);
  const indexHtmlPath = path.resolve(frontendDir, INDEX_HTML_NAME);

  logger.info('静态文件服务初始化', { frontendDir, indexHtmlPath });

  if (!fs.existsSync(frontendDir)) {
    logger.warn('前端目录不存在，跳过静态文件服务', { frontendDir });
    return;
  }

  const staticHandler = expressStatic(frontendDir);
  app.use(staticHandler);

  const indexHtmlExists = fs.existsSync(indexHtmlPath);
  if (!indexHtmlExists) {
    logger.warn('index.html 不存在，跳过 SPA 路由回退', { indexHtmlPath });
    return;
  }

  app.get('/*', (req: Request, res: Response, next: NextFunction): void => {
    if (req.path.startsWith('/api/') || req.path.startsWith('/health')) {
      return next();
    }

    if (req.path.includes('.') && path.extname(req.path) !== '') {
      return next();
    }

    try {
      const nonce = req.nonce || '';
      let html = fs.readFileSync(indexHtmlPath, 'utf-8');
      html = html.split(NONCE_PLACEHOLDER).join(nonce);
      html = html.replace(/__NONCE__/g, nonce);
      html = html.replace(/\{\{nonce\}\}/g, nonce);
      html = html.replace(/%NONCE%/g, nonce);

      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');

      res.send(html);
    } catch (error) {
      logger.error('index.html 读取或注入失败', {
        error: error instanceof Error ? error.message : String(error),
        path: req.path,
      });
      next(error);
    }
  });

  logger.info('前端静态文件服务已挂载', { frontendDir });
}

function expressStatic(rootDir: string) {
  const express = require('express');
  return express.static(rootDir, {
    index: false,
    dotfiles: 'deny',
    etag: true,
    lastModified: true,
    maxAge: '1h',
    immutable: false,
    setHeaders: (res: Response, filePath: string) => {
      const ext = path.extname(filePath).toLowerCase();
      if (['.html', '.htm'].includes(ext)) {
        res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
      } else if (['.css', '.js', '.mjs', '.woff', '.woff2', '.ttf', '.eot', '.otf'].includes(ext)) {
        res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
      } else if (['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp'].includes(ext)) {
        res.setHeader('Cache-Control', 'public, max-age=86400');
      }
    },
  });
}

export default serveFrontend;
