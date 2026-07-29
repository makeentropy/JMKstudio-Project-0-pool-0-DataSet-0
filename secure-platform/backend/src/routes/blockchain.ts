import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import rateLimit from 'express-rate-limit';
import {
  Blockchain,
  DistributedNode,
} from '../modules/blockchain';
import { ApiError } from '../app';
import logger from '../utils/logger';

const router = Router();

const blockchain = new Blockchain();
const distributedNode = new DistributedNode(blockchain);

const requireAuth = (req: Request, _res: Response, next: NextFunction): void => {
  const userId = req.session?.userId;
  if (!userId) {
    return next(new ApiError('未登录或登录已过期', { statusCode: 401, code: 'UNAUTHORIZED' }));
  }
  next();
};

const publicLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 60,
  standardHeaders: true,
  legacyHeaders: false,
  handler: (_req: Request, res: Response): void => {
    res.status(429).json({
      success: false,
      message: '请求过于频繁，请稍后再试',
      code: 'RATE_LIMIT_EXCEEDED',
    });
  },
});

const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request): string => {
    const userId = (req.session && req.session.userId) || 'anonymous';
    return `${req.ip}:${userId}`;
  },
  handler: (_req: Request, res: Response): void => {
    res.status(429).json({
      success: false,
      message: '区块链请求过于频繁，请稍后再试',
      code: 'RATE_LIMIT_EXCEEDED',
    });
  },
});

router.use(publicLimiter);

const storeDataSchema = z.object({
  data: z.unknown(),
});

router.post('/store', requireAuth, authLimiter, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const userId = req.session!.userId!;
    const parsed = storeDataSchema.parse(req.body);

    const result = blockchain.storeOnChain(parsed.data, userId);

    logger.info('数据存证上链', {
      userId,
      txId: result.txId,
      blockIndex: result.blockIndex,
      dataHash: result.dataHash,
    });

    res.json({
      success: true,
      data: {
        txId: result.txId,
        blockIndex: result.blockIndex,
        dataHash: result.dataHash,
        confirmations: blockchain.getChain().length - result.blockIndex,
      },
    });
  } catch (error) {
    next(error);
  }
});

const verifyDataSchema = z.object({
  data: z.unknown(),
  txId: z.string().min(1).optional(),
});

router.post('/verify', publicLimiter, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = verifyDataSchema.parse(req.body);
    const result = blockchain.verifyData(parsed.data, parsed.txId);

    res.json({
      success: true,
      data: {
        exists: result.exists,
        blockIndex: result.blockIndex,
        blockHash: result.blockHash,
        confirmations: result.confirmations,
      },
    });
  } catch (error) {
    next(error);
  }
});

router.get('/chain', publicLimiter, (_req: Request, res: Response, next: NextFunction): void => {
  try {
    const recentBlocks = blockchain.getRecentBlocks(10);
    const chainState = blockchain.getChainState();

    res.json({
      success: true,
      data: {
        chainState: {
          blockCount: chainState.blockCount,
          totalTransactions: chainState.totalTransactions,
          difficulty: chainState.difficulty,
          isHealthy: chainState.isHealthy,
          latestBlockHash: chainState.latestBlock.hash,
          latestBlockIndex: chainState.latestBlock.index,
        },
        recentBlocks: recentBlocks.map((block) => ({
          index: block.index,
          hash: block.hash,
          previousHash: block.previousHash,
          timestamp: block.timestamp,
          transactionCount: block.transactions.length,
          nonce: block.nonce,
          merkleRoot: block.merkleRoot,
        })),
        pendingTransactionCount: blockchain.getPendingTransactionCount(),
      },
    });
  } catch (error) {
    next(error);
  }
});

router.get('/mine', requireAuth, authLimiter, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const userId = req.session!.userId!;
    const pendingCount = blockchain.getPendingTransactionCount();

    if (pendingCount === 0) {
      blockchain.storeOnChain(
        { type: 'EMPTY_BLOCK_MINED', timestamp: Date.now() },
        userId
      );
    }

    const block = blockchain.minePendingTransactions(userId);
    distributedNode.broadcastBlock(block);

    logger.info('用户挖矿成功', {
      userId,
      blockIndex: block.index,
      txCount: block.transactions.length,
    });

    res.json({
      success: true,
      data: {
        block: {
          index: block.index,
          hash: block.hash,
          previousHash: block.previousHash,
          timestamp: block.timestamp,
          transactionCount: block.transactions.length,
          nonce: block.nonce,
          merkleRoot: block.merkleRoot,
        },
        minerAddress: userId,
      },
    });
  } catch (error) {
    next(error);
  }
});

const connectPeerSchema = z.object({
  url: z.string().url({ message: '必须是有效的URL' }),
});

router.post('/peer/connect', requireAuth, authLimiter, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = connectPeerSchema.parse(req.body);
    const connected = distributedNode.connectToPeer(parsed.url);

    res.json({
      success: true,
      data: {
        connected,
        peerUrl: parsed.url,
        totalPeers: distributedNode.getPeers().length,
      },
    });
  } catch (error) {
    next(error);
  }
});

const disconnectPeerSchema = z.object({
  url: z.string().url().optional(),
});

router.post('/peer/disconnect', requireAuth, authLimiter, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = disconnectPeerSchema.parse(req.body);
    const url = parsed.url;
    if (url) {
      const disconnected = distributedNode.disconnectPeer(url);
      res.json({
        success: true,
        data: {
          disconnected,
          peerUrl: url,
          totalPeers: distributedNode.getPeers().length,
        },
      });
    } else {
      const peers = distributedNode.getPeerUrls();
      for (const peerUrl of peers) {
        distributedNode.disconnectPeer(peerUrl);
      }
      res.json({
        success: true,
        data: {
          disconnected: peers.length,
          totalPeers: 0,
        },
      });
    }
  } catch (error) {
    next(error);
  }
});

router.get('/peers', requireAuth, authLimiter, (_req: Request, res: Response, next: NextFunction): void => {
  try {
    const peers = distributedNode.getPeers();

    res.json({
      success: true,
      data: {
        nodeId: distributedNode.nodeId,
        count: peers.length,
        peers,
      },
    });
  } catch (error) {
    next(error);
  }
});

router.post('/peer/sync', requireAuth, authLimiter, async (_req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const chain = await distributedNode.syncChain();

    res.json({
      success: true,
      data: {
        synced: true,
        chainHeight: chain.length,
        blockCount: chain.length,
      },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
export { router as blockchainRoutes, blockchain, distributedNode };
