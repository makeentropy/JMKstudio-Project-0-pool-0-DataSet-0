import { Router, Request, Response } from 'express';

const router = Router();

router.get('/', (_req: Request, res: Response): void => {
  res.json({
    success: true,
    data: {
      module: 'access-auth',
      status: 'placeholder',
      message: '权限认证模块占位路由',
    },
  });
});

router.post('/login', (_req: Request, res: Response): void => {
  res.json({
    success: true,
    data: {
      message: '登录接口占位',
    },
  });
});

router.post('/logout', (_req: Request, res: Response): void => {
  res.json({
    success: true,
    data: {
      message: '登出接口占位',
    },
  });
});

export default router;
export { router as accessAuthRoutes };
