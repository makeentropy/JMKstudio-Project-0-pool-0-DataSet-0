import { v4 as uuidv4 } from 'uuid';
import type {
  Block,
  Transaction,
  ChainState,
  StoreDataResult,
  VerifyDataResult,
} from './types';
import { BlockUtils } from './block';
import logger from '../../utils/logger';
import { ApiError } from '../../app';

const MINING_REWARD = 50;
const DEFAULT_DIFFICULTY = 4;

export class Blockchain {
  protected chain: Block[];
  protected pendingTransactions: Transaction[];
  protected difficulty: number;
  private dataProofIndex: Map<string, { txId: string; blockIndex: number }> = new Map();

  constructor(difficulty: number = DEFAULT_DIFFICULTY) {
    this.chain = [BlockUtils.generateGenesisBlock()];
    this.pendingTransactions = [];
    this.difficulty = difficulty;
    this.buildDataProofIndex();
  }

  private buildDataProofIndex(): void {
    this.dataProofIndex.clear();
    for (const block of this.chain) {
      for (const tx of block.transactions) {
        if (tx.sender === 'PROOF' || tx.sender === 'SYSTEM') {
          try {
            const parsed = JSON.parse(tx.data);
            if (parsed && parsed.dataHash) {
              this.dataProofIndex.set(parsed.dataHash, {
                txId: tx.id,
                blockIndex: block.index,
              });
            }
          } catch {
            this.dataProofIndex.set(tx.data, {
              txId: tx.id,
              blockIndex: block.index,
            });
          }
        }
      }
    }
  }

  addTransaction(tx: Transaction, senderPubKey?: string, signature?: string): boolean {
    if (senderPubKey) {
      const txToVerify = signature ? { ...tx, signature } : tx;
      if (!BlockUtils.verifyTransactionSignature(txToVerify, senderPubKey)) {
        logger.warn('区块链交易签名验证失败', { txId: tx.id });
        return false;
      }
    }

    if (!tx.id || !tx.sender || !tx.recipient) {
      return false;
    }

    this.pendingTransactions.push(tx);
    logger.debug('交易已加入待处理池', { txId: tx.id, pendingCount: this.pendingTransactions.length });
    return true;
  }

  minePendingTransactions(minerAddress: string): Block {
    const coinbaseTx: Transaction = {
      id: uuidv4(),
      sender: 'SYSTEM',
      recipient: minerAddress,
      data: JSON.stringify({ type: 'MINING_REWARD', amount: MINING_REWARD }),
      timestamp: Date.now(),
    };

    const transactionsToMine = [...this.pendingTransactions, coinbaseTx];
    const merkleRoot = BlockUtils.calculateMerkleRoot(transactionsToMine);

    const lastBlock = this.getLatestBlock();
    const blockWithoutHashNonce: Omit<Block, 'hash' | 'nonce'> = {
      index: lastBlock.index + 1,
      timestamp: Date.now(),
      transactions: transactionsToMine,
      previousHash: lastBlock.hash,
      merkleRoot,
    };

    const minedBlock = BlockUtils.mineBlock(blockWithoutHashNonce, this.difficulty);

    if (BlockUtils.isBlockValid(minedBlock, lastBlock)) {
      this.chain.push(minedBlock);
      this.pendingTransactions = [];

      for (const tx of minedBlock.transactions) {
        if (tx.sender === 'PROOF' || tx.sender === 'SYSTEM') {
          try {
            const parsed = JSON.parse(tx.data);
            if (parsed && parsed.dataHash) {
              this.dataProofIndex.set(parsed.dataHash, {
                txId: tx.id,
                blockIndex: minedBlock.index,
              });
            }
          } catch {
            this.dataProofIndex.set(tx.data, {
              txId: tx.id,
              blockIndex: minedBlock.index,
            });
          }
        }
      }

      logger.info('新区块挖出', {
        blockIndex: minedBlock.index,
        txCount: minedBlock.transactions.length,
        miner: minerAddress,
        nonce: minedBlock.nonce,
      });

      return minedBlock;
    }

    throw new ApiError('挖矿失败：区块验证失败', { statusCode: 500, code: 'BLOCK_MINING_FAILED' });
  }

  getChain(): Block[] {
    return [...this.chain];
  }

  getLatestBlock(): Block {
    return this.chain[this.chain.length - 1]!;
  }

  isChainValid(): boolean {
    for (let i = 1; i < this.chain.length; i++) {
      const currentBlock = this.chain[i]!;
      const previousBlock = this.chain[i - 1]!;

      if (!BlockUtils.isBlockValid(currentBlock, previousBlock)) {
        logger.warn('区块链验证失败', { blockIndex: currentBlock.index });
        return false;
      }

      for (const tx of currentBlock.transactions) {
        if (tx.sender !== 'SYSTEM' && tx.sender !== 'GENESIS' && tx.sender !== 'PROOF') {
          if (!tx.signature) {
            continue;
          }
        }
      }
    }
    return true;
  }

  getBalance(address: string): number {
    let balance = 0;

    for (const block of this.chain) {
      for (const tx of block.transactions) {
        if (tx.recipient === address) {
          try {
            const parsed = JSON.parse(tx.data);
            if (parsed && typeof parsed.amount === 'number') {
              balance += parsed.amount;
            }
          } catch {
            continue;
          }
        }
        if (tx.sender === address) {
          try {
            const parsed = JSON.parse(tx.data);
            if (parsed && typeof parsed.amount === 'number') {
              balance -= parsed.amount;
            }
          } catch {
            continue;
          }
        }
      }
    }

    return balance;
  }

  storeOnChain(data: unknown, owner: string): StoreDataResult {
    const dataHash = BlockUtils.hashData(data);
    const timestamp = Date.now();

    const existingProof = this.dataProofIndex.get(dataHash);
    if (existingProof) {
      return {
        txId: existingProof.txId,
        blockIndex: existingProof.blockIndex,
        dataHash,
      };
    }

    const tx: Transaction = {
      id: uuidv4(),
      sender: 'PROOF',
      recipient: owner,
      data: JSON.stringify({
        dataHash,
        owner,
        timestamp,
        originalType: typeof data,
      }),
      timestamp,
    };

    this.addTransaction(tx);

    const minedBlock = this.minePendingTransactions(owner);

    this.dataProofIndex.set(dataHash, {
      txId: tx.id,
      blockIndex: minedBlock.index,
    });

    logger.info('数据存证上链成功', { dataHash, blockIndex: minedBlock.index, owner });

    return {
      txId: tx.id,
      blockIndex: minedBlock.index,
      dataHash,
    };
  }

  verifyData(data: unknown, txId?: string): VerifyDataResult {
    const dataHash = BlockUtils.hashData(data);

    if (txId) {
      for (const block of this.chain) {
        const tx = block.transactions.find((t) => t.id === txId);
        if (tx) {
          try {
            const parsed = JSON.parse(tx.data);
            if (parsed && parsed.dataHash === dataHash) {
              return {
                exists: true,
                blockIndex: block.index,
                blockHash: block.hash,
                confirmations: this.chain.length - block.index,
              };
            }
          } catch {
            if (tx.data === dataHash) {
              return {
                exists: true,
                blockIndex: block.index,
                blockHash: block.hash,
                confirmations: this.chain.length - block.index,
              };
            }
          }
        }
      }
    }

    const indexedProof = this.dataProofIndex.get(dataHash);
    if (indexedProof) {
      const block = this.chain[indexedProof.blockIndex];
      if (block) {
        return {
          exists: true,
          blockIndex: indexedProof.blockIndex,
          blockHash: block.hash,
          confirmations: this.chain.length - indexedProof.blockIndex,
        };
      }
    }

    for (const block of this.chain) {
      for (const tx of block.transactions) {
        if (tx.sender === 'PROOF' || tx.sender === 'SYSTEM') {
          try {
            const parsed = JSON.parse(tx.data);
            if (parsed && parsed.dataHash === dataHash) {
              return {
                exists: true,
                blockIndex: block.index,
                blockHash: block.hash,
                confirmations: this.chain.length - block.index,
              };
            }
          } catch {
            if (tx.data === dataHash) {
              return {
                exists: true,
                blockIndex: block.index,
                blockHash: block.hash,
                confirmations: this.chain.length - block.index,
              };
            }
          }
        }
      }
    }

    return {
      exists: false,
      blockIndex: -1,
      blockHash: '',
      confirmations: 0,
    };
  }

  replaceChain(newChain: Block[]): boolean {
    if (newChain.length <= this.chain.length) {
      logger.warn('替换链失败：新链长度不大于当前链', {
        currentLength: this.chain.length,
        newLength: newChain.length,
      });
      return false;
    }

    for (let i = 1; i < newChain.length; i++) {
      if (!BlockUtils.isBlockValid(newChain[i]!, newChain[i - 1]!)) {
        logger.warn('替换链失败：新链验证失败', { blockIndex: i });
        return false;
      }
    }

    const oldLength = this.chain.length;
    this.chain = newChain;
    this.buildDataProofIndex();

    logger.info('区块链已替换（最长链原则）', { oldLength, newLength: this.chain.length });
    return true;
  }

  getChainState(): ChainState {
    const latestBlock = this.getLatestBlock();
    let totalTransactions = 0;
    for (const block of this.chain) {
      totalTransactions += block.transactions.length;
    }

    return {
      latestBlock,
      blockCount: this.chain.length,
      totalTransactions,
      difficulty: this.difficulty,
      isHealthy: this.isChainValid(),
    };
  }

  getRecentBlocks(limit: number = 10): Block[] {
    if (limit <= 0) limit = 10;
    return this.chain.slice(-limit).reverse();
  }

  getPendingTransactionCount(): number {
    return this.pendingTransactions.length;
  }
}

export default Blockchain;
