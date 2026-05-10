import { create } from 'zustand';

export interface Snapshot {
  id: string;
  name: string;
  path: string;
  size: number;
  createdAt: string;
  status: 'available' | 'creating' | 'restoring';
}

export interface StorageStats {
  total: number;
  used: number;
  available: number;
  compressionRatio: number;
}

export interface Container {
  id: string;
  name: string;
  image: string;
  status: 'running' | 'stopped' | 'created';
  ports: string[];
  createdAt: string;
}

interface AppState {
  snapshots: Snapshot[];
  storageStats: StorageStats | null;
  containers: Container[];
  loading: boolean;
  setSnapshots: (snapshots: Snapshot[]) => void;
  setStorageStats: (stats: StorageStats) => void;
  setContainers: (containers: Container[]) => void;
  setLoading: (loading: boolean) => void;
  addSnapshot: (snapshot: Snapshot) => void;
  updateSnapshot: (id: string, updates: Partial<Snapshot>) => void;
  removeSnapshot: (id: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  snapshots: [],
  storageStats: null,
  containers: [],
  loading: false,
  setSnapshots: (snapshots) => set({ snapshots }),
  setStorageStats: (stats) => set({ storageStats: stats }),
  setContainers: (containers) => set({ containers }),
  setLoading: (loading) => set({ loading }),
  addSnapshot: (snapshot) => set((state) => ({ snapshots: [...state.snapshots, snapshot] })),
  updateSnapshot: (id, updates) => set((state) => ({
    snapshots: state.snapshots.map((s) => s.id === id ? { ...s, ...updates } : s)
  })),
  removeSnapshot: (id) => set((state) => ({
    snapshots: state.snapshots.filter((s) => s.id !== id)
  })),
}));
