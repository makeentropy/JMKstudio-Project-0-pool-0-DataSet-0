import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import type { Block, Transaction } from './types';

export class BlockUtils {
  static calculateHash(block: Omit<Block, 'hash'>): string {
    const data = `${block.index}:${block.timestamp}:${block.merkleRoot}:${block.previousHash}:${block.nonce}`;
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  static calculateMerkleRoot(transactions: Transaction[]): string {
    if (transactions.length === 0) {
      return crypto.createHash('sha256').update('empty').digest('hex');
    }

    let hashes = transactions.map((tx) =>
      crypto.createHash('sha256').update(`${tx.id}:${tx.sender}:${tx.recipient}:${tx.data}:${tx.timestamp}`).digest('hex')
    );

    while (hashes.length > 1) {
      const nextLevel: string[] = [];
      for (let i = 0; i < hashes.length; i += 2) {
        const left = hashes[i];
        const right = hashes[i + 1] ?? hashes[i];
        const combined = crypto.createHash('sha256').update(left + right).digest('hex');
        nextLevel.push(combined);
      }
      hashes = nextLevel;
    }

    return hashes[0]!;
  }

  static generateGenesisBlock(): Block {
    const genesisTx: Transaction = {
      id: uuidv4(),
      sender: 'GENESIS',
      recipient: 'GENESIS',
      data: 'Genesis Block',
      timestamp: Date.now(),
    };

    const transactions = [genesisTx];
    const merkleRoot = this.calculateMerkleRoot(transactions);

    const blockWithoutHash: Omit<Block, 'hash'> = {
      index: 0,
      timestamp: Date.now(),
      transactions,
      previousHash: '0'.repeat(64),
      nonce: 0,
      merkleRoot,
    };

    const hash = this.calculateHash(blockWithoutHash);

    return {
      ...blockWithoutHash,
      hash,
    };
  }

  static isBlockValid(newBlock: Block, previousBlock: Block): boolean {
    if (previousBlock.index + 1 !== newBlock.index) {
      return false;
    }

    if (previousBlock.hash !== newBlock.previousHash) {
      return false;
    }

    const computedMerkleRoot = this.calculateMerkleRoot(newBlock.transactions);
    if (computedMerkleRoot !== newBlock.merkleRoot) {
      return false;
    }

    const blockWithoutHash: Omit<Block, 'hash'> = {
      index: newBlock.index,
      timestamp: newBlock.timestamp,
      transactions: newBlock.transactions,
      previousHash: newBlock.previousHash,
      nonce: newBlock.nonce,
      merkleRoot: newBlock.merkleRoot,
    };
    const computedHash = this.calculateHash(blockWithoutHash);
    if (computedHash !== newBlock.hash) {
      return false;
    }

    return true;
  }

  static mineBlock(block: Omit<Block, 'hash' | 'nonce'>, difficulty: number = 4): Block {
    const target = '0'.repeat(difficulty);
    let nonce = 0;
    const merkleRoot = block.merkleRoot || this.calculateMerkleRoot(block.transactions);

    while (true) {
      const candidate: Omit<Block, 'hash'> = {
        ...block,
        merkleRoot,
        nonce,
      };

      const hash = this.calculateHash(candidate);
      if (hash.startsWith(target)) {
        return {
          ...candidate,
          hash,
        };
      }
      nonce++;
    }
  }

  static hashData(data: unknown): string {
    const serialized = typeof data === 'string' ? data : JSON.stringify(data);
    return crypto.createHash('sha256').update(serialized).digest('hex');
  }

  static createTransaction(
    sender: string,
    recipient: string,
    data: unknown,
    senderPrivateKey?: string
  ): Transaction {
    const serializedData = typeof data === 'string' ? data : JSON.stringify(data);
    const timestamp = Date.now();
    const id = uuidv4();

    const tx: Transaction = {
      id,
      sender,
      recipient,
      data: serializedData,
      timestamp,
    };

    if (senderPrivateKey) {
      const signContent = `${id}:${sender}:${recipient}:${serializedData}:${timestamp}`;
      const sign = crypto.createSign('RSA-SHA256');
      sign.update(signContent);
      try {
        tx.signature = sign.sign(senderPrivateKey, 'base64');
      } catch {
        tx.signature = undefined;
      }
    }

    return tx;
  }

  static verifyTransactionSignature(tx: Transaction, senderPublicKey: string): boolean {
    if (!tx.signature) {
      return tx.sender === 'SYSTEM' || tx.sender === 'GENESIS';
    }
    const signContent = `${tx.id}:${tx.sender}:${tx.recipient}:${tx.data}:${tx.timestamp}`;
    const verify = crypto.createVerify('RSA-SHA256');
    verify.update(signContent);
    try {
      return verify.verify(senderPublicKey, tx.signature, 'base64');
    } catch {
      return false;
    }
  }
}

export default BlockUtils;
