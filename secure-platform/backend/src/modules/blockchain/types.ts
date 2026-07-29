export interface Transaction {
  id: string;
  sender: string;
  recipient: string;
  data: string;
  timestamp: number;
  signature?: string;
}

export interface Block {
  index: number;
  timestamp: number;
  transactions: Transaction[];
  previousHash: string;
  hash: string;
  nonce: number;
  merkleRoot: string;
}

export interface ChainState {
  latestBlock: Block;
  blockCount: number;
  totalTransactions: number;
  difficulty: number;
  isHealthy: boolean;
}

export interface StoreDataResult {
  txId: string;
  blockIndex: number;
  dataHash: string;
}

export interface VerifyDataResult {
  exists: boolean;
  blockIndex: number;
  blockHash: string;
  confirmations: number;
}

export interface PeerInfo {
  url: string;
  connectedAt: number;
  lastSyncAt?: number;
}
