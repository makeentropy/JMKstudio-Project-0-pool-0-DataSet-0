import http from 'http';
import type { AddressInfo } from 'net';
import { createApp } from './app';
import { config } from './config';
import logger from './utils/logger';
import { createRedisClient } from './middleware/security';
import Redis from 'ioredis';

export interface ServerContext {
  server: http.Server;
  app: ReturnType<typeof createApp>;
  redisClient: Redis;
  shutdown: (signal?: string) => Promise<void>;
}

let isShuttingDown = false;

const createGracefulShutdown = (
  server: http.Server,
  redisClient: Redis
): ((signal?: string) => Promise<void>) => {
  let shutdownPromise: Promise<void> | null = null;

  return async (signal?: string): Promise<void> => {
    if (shutdownPromise) {
      return shutdownPromise;
    }

    if (isShuttingDown) {
      logger.warn('收到重复关闭信号，忽略', { signal });
      return;
    }

    isShuttingDown = true;
    logger.info('开始优雅关闭服务器', { signal });

    shutdownPromise = (async (): Promise<void> => {
      const shutdownTimeout = setTimeout(() => {
        logger.error('优雅关闭超时，强制退出');
        process.exit(1);
      }, 30000);
      shutdownTimeout.unref();

      try {
        logger.info('停止接受新连接...');
        server.close(() => {
          logger.info('HTTP服务器已停止接受新连接');
        });

        const closePromises: Promise<void>[] = [];

        closePromises.push(
          new Promise<void>((resolve) => {
            const forceTimer = setTimeout(() => {
              logger.warn('HTTP连接关闭超时，强制关闭');
              resolve();
            }, 10000);
            forceTimer.unref();

            server.closeAllConnections?.();
            server.closeIdleConnections?.();

            server.once('close', () => {
              clearTimeout(forceTimer);
              resolve();
            });

            if (server.listening === false) {
              clearTimeout(forceTimer);
              resolve();
            }
          })
        );

        closePromises.push(
          (async (): Promise<void> => {
            logger.info('断开Redis连接...');
            try {
              await redisClient.quit();
              logger.info('Redis连接已断开');
            } catch (redisError) {
              logger.error('Redis断开连接出错', {
                error: redisError instanceof Error ? redisError.message : String(redisError),
              });
            }
          })()
        );

        await Promise.allSettled(closePromises);
        clearTimeout(shutdownTimeout);

        logger.info('服务器优雅关闭完成');
        process.exit(0);
      } catch (error) {
        clearTimeout(shutdownTimeout);
        logger.error('优雅关闭过程出错', {
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        });
        process.exit(1);
      }
    })();

    return shutdownPromise;
  };
};

export const startServer = async (): Promise<ServerContext> => {
  try {
    logger.info('正在启动服务器...', {
      nodeEnv: config.app.nodeEnv,
      port: config.app.port,
    });

    const redisClient = createRedisClient();

    logger.info('连接Redis...', {
      host: config.redis.host,
      port: config.redis.port,
      db: config.redis.db,
    });

    try {
      await redisClient.connect();
      logger.info('Redis连接成功');
    } catch (redisError) {
      logger.error('Redis连接失败', {
        error: redisError instanceof Error ? redisError.message : String(redisError),
      });
      if (config.app.nodeEnv === 'production') {
        throw redisError;
      }
      logger.warn('开发环境下继续启动，Redis连接可能稍后恢复');
    }

    const app = createApp({ redisClient });
    const server = http.createServer(app);

    server.on('clientError', (err: Error, socket) => {
      logger.warn('客户端连接错误', {
        error: err.message,
        code: (err as NodeJS.ErrnoException).code,
      });
      if (socket.writable) {
        socket.end('HTTP/1.1 400 Bad Request\r\n\r\n');
      }
    });

    server.on('error', (err: NodeJS.ErrnoException) => {
      if (err.code === 'EADDRINUSE') {
        logger.error(`端口 ${config.app.port} 已被占用`);
      } else {
        logger.error('服务器错误', {
          error: err.message,
          code: err.code,
        });
      }
      if (!server.listening) {
        process.exit(1);
      }
    });

    return new Promise<ServerContext>((resolve, reject) => {
      const startupTimeout = setTimeout(() => {
        reject(new Error('服务器启动超时'));
      }, 30000);
      startupTimeout.unref();

      server.listen(config.app.port, '0.0.0.0', () => {
        clearTimeout(startupTimeout);
        const address = server.address() as AddressInfo;
        logger.info('服务器启动成功', {
          host: address.address,
          port: address.port,
          protocol: 'http',
          url: `http://${address.address === '::' || address.address === '0.0.0.0' ? 'localhost' : address.address}:${address.port}`,
          apiPrefix: config.app.apiPrefix,
          pid: process.pid,
        });

        const shutdown = createGracefulShutdown(server, redisClient);

        const signals: NodeJS.Signals[] = ['SIGTERM', 'SIGINT', 'SIGUSR2'];
        signals.forEach((signal) => {
          process.on(signal, () => {
            logger.info(`收到信号: ${signal}`);
            void shutdown(signal);
          });
        });

        resolve({ server, app, redisClient, shutdown });
      });

      server.once('error', (err) => {
        clearTimeout(startupTimeout);
        reject(err);
      });
    });
  } catch (error) {
    logger.error('服务器启动失败', {
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    process.exit(1);
  }
};

if (require.main === module) {
  void startServer();
}

export default startServer;
