import { Router, Request, Response } from 'express';

const router = Router();

router.get('/', (_req: Request, res: Response): void => {
  res.json({
    success: true,
    data: {
      module: 'access-admin',
      status: 'placeholder',
      message: '管理员模块占位路由',
    },
  });
});

export default router;
export { router as accessAdminRoutes };
