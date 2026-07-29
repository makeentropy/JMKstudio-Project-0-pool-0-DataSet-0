import { v4 as uuidv4 } from 'uuid';
import type { Block, Transaction, PeerInfo } from './types';
import { Blockchain } from './chain';
import logger from '../../utils/logger';
import { ApiError } from '../../app';

export class DistributedNode {
  public readonly nodeId: string;
  private peers: Map<string, PeerInfo> = new Map();
  private blockchain: Blockchain;
  private messageHandlers: Map<string, (payload: unknown, fromPeer: string) => void> = new Map();

  constructor(blockchain: Blockchain, nodeId?: string) {
    this.blockchain = blockchain;
    this.nodeId = nodeId || `node_${uuidv4().substring(0, 8)}`;
    this.setupDefaultHandlers();
  }

  private setupDefaultHandlers(): void {
    this.messageHandlers.set('NEW_BLOCK', (payload, fromPeer) => {
      const block = payload as Block;
      this.handleIncomingBlock(block, fromPeer);
    });

    this.messageHandlers.set('NEW_TRANSACTION', (payload, fromPeer) => {
      const tx = payload as Transaction;
      this.handleIncomingTransaction(tx, fromPeer);
    });

    this.messageHandlers.set('CHAIN_REQUEST', (_payload, fromPeer) => {
      this.sendToPeer(fromPeer, 'CHAIN_RESPONSE', this.blockchain.getChain());
    });

    this.messageHandlers.set('CHAIN_RESPONSE', (payload) => {
      const chain = payload as Block[];
      this.blockchain.replaceChain(chain);
    });

    this.messageHandlers.set('PING', (_payload, fromPeer) => {
      this.sendToPeer(fromPeer, 'PONG', {
        nodeId: this.nodeId,
        timestamp: Date.now(),
        chainHeight: this.blockchain.getChain().length,
      });
    });
  }

  connectToPeer(url: string): boolean {
    if (!url || typeof url !== 'string') {
      throw new ApiError('节点URL无效', { statusCode: 400, code: 'INVALID_PEER_URL' });
    }

    if (this.peers.has(url)) {
      logger.info('已连接到此节点，跳过', { peerUrl: url });
      return false;
    }

    this.peers.set(url, {
      url,
      connectedAt: Date.now(),
    });

    logger.info('连接到新节点', { nodeId: this.nodeId, peerUrl: url });
    return true;
  }

  disconnectPeer(url: string): boolean {
    const removed = this.peers.delete(url);
    if (removed) {
      logger.info('断开节点连接', { nodeId: this.nodeId, peerUrl: url });
    }
    return removed;
  }

  getPeers(): PeerInfo[] {
    return Array.from(this.peers.values());
  }

  getPeerUrls(): string[] {
    return Array.from(this.peers.keys());
  }

  private sendToPeer(url: string, messageType: string, payload: unknown): void {
    logger.debug('发送消息到节点', {
      from: this.nodeId,
      to: url,
      messageType,
    });

    const handler = this.messageHandlers.get(messageType);
    if (handler) {
      try {
        handler(payload, url);
      } catch (error) {
        logger.error('处理节点消息失败', {
          messageType,
          fromPeer: url,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }
  }

  broadcastBlock(block: Block): void {
    logger.info('广播新区块', {
      nodeId: this.nodeId,
      blockIndex: block.index,
      txCount: block.transactions.length,
      peerCount: this.peers.size,
    });

    for (const peerUrl of this.peers.keys()) {
      this.sendToPeer(peerUrl, 'NEW_BLOCK', block);
    }
  }

  broadcastTransaction(tx: Transaction): void {
    logger.debug('广播交易', {
      nodeId: this.nodeId,
      txId: tx.id,
      peerCount: this.peers.size,
    });

    for (const peerUrl of this.peers.keys()) {
      this.sendToPeer(peerUrl, 'NEW_TRANSACTION', tx);
    }
  }

  private handleIncomingBlock(block: Block, fromPeer: string): void {
    const latestBlock = this.blockchain.getLatestBlock();

    if (block.index <= latestBlock.index) {
      return;
    }

    if (block.index === latestBlock.index + 1) {
      try {
        const chain = this.blockchain.getChain();
        const isValid = (block as Block & { previousHash?: string }).previousHash === latestBlock.hash;
        if (isValid) {
          const newChain = [...chain, block];
          this.blockchain.replaceChain(newChain);
          this.broadcastBlock(block);
          logger.info('接收并附加新区块', { blockIndex: block.index, fromPeer });
        }
      } catch (error) {
        logger.warn('处理入站区块失败，触发链同步', {
          error: error instanceof Error ? error.message : String(error),
        });
        void this.syncChain();
      }
    } else {
      logger.info('检测到链差距，触发同步', {
        localIndex: latestBlock.index,
        remoteIndex: block.index,
        fromPeer,
      });
      void this.syncChain();
    }
  }

  private handleIncomingTransaction(tx: Transaction, fromPeer: string): void {
    const added = this.blockchain.addTransaction(tx);
    if (added) {
      this.broadcastTransaction(tx);
      logger.debug('接收并转发交易', { txId: tx.id, fromPeer });
    }
  }

  async syncChain(): Promise<Block[]> {
    logger.info('开始从节点同步链', { nodeId: this.nodeId, peerCount: this.peers.size });

    const candidateChains: Block[][] = [];
    const localChain = this.blockchain.getChain();
    candidateChains.push(localChain);

    for (const peerUrl of this.peers.keys()) {
      try {
        logger.debug('请求节点链数据', { peerUrl });
        const peerChain = this.simulateFetchPeerChain(peerUrl);
        if (peerChain && peerChain.length > 0) {
          candidateChains.push(peerChain);
        }
      } catch (error) {
        logger.warn('从节点拉取链失败', {
          peerUrl,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    let bestChain = localChain;
    for (const chain of candidateChains) {
      if (chain.length > bestChain.length) {
        const tempBlockchain = new Blockchain();
        let isValid = chain.length > 0;
        for (let i = 1; isValid && i < chain.length; i++) {
          try {
            const prev = chain[i - 1]!;
            const curr = chain[i]!;
            const blockWithoutHash = {
              index: curr.index,
              timestamp: curr.timestamp,
              transactions: curr.transactions,
              previousHash: curr.previousHash,
              nonce: curr.nonce,
              merkleRoot: curr.merkleRoot,
            };
            const computedHash = (() => {
              const { BlockUtils } = require('./block') as typeof import('./block');
              return BlockUtils.calculateHash(blockWithoutHash);
            })();
            isValid = computedHash === curr.hash && curr.previousHash === prev.hash;
          } catch {
            isValid = false;
          }
        }
        if (isValid) {
          bestChain = chain;
        }
      }
    }

    const replaced = this.blockchain.replaceChain(bestChain);
    if (replaced) {
      logger.info('链同步完成，已替换为最长有效链', { newHeight: bestChain.length });
    } else {
      logger.info('链同步完成，保持现有链', { height: this.blockchain.getChain().length });
    }

    for (const peerUrl of this.peers.keys()) {
      const peer = this.peers.get(peerUrl);
      if (peer) {
        peer.lastSyncAt = Date.now();
      }
    }

    return this.blockchain.getChain();
  }

  private simulateFetchPeerChain(peerUrl: string): Block[] | null {
    logger.debug('模拟从节点拉取链', { peerUrl });

    if (peerUrl.startsWith('http://trusted-peer')) {
      const trustedBlockchain = new Blockchain();
      for (let i = 0; i < 2; i++) {
        trustedBlockchain.minePendingTransactions('trusted-miner');
      }
      return trustedBlockchain.getChain();
    }

    return null;
  }

  onMessage(messageType: string, handler: (payload: unknown, fromPeer: string) => void): void {
    this.messageHandlers.set(messageType, handler);
  }

  getBlockchain(): Blockchain {
    return this.blockchain;
  }
}

export default DistributedNode;
