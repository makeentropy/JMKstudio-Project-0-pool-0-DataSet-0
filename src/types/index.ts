export type ViewType = 'dashboard' | 'generator' | 'builder' | 'pusher';

export type ProjectTemplate = 'dataset-builder' | 'model-training' | 'pipeline' | 'xor-pool' | 'custom';

export type ProjectStatus = 'idle' | 'generating' | 'coding' | 'building' | 'pushing' | 'completed' | 'error';

export interface DriverConfig {
  type: 'xor-pool' | 'base-xor';
  poolSize?: number;
  redundancyLevel?: number;
}

export interface BuildRecord {
  id: string;
  projectId: string;
  status: 'success' | 'failed' | 'in-progress';
  logs: string;
  duration: number;
  artifacts: string[];
  timestamp: Date;
}

export interface PushRecord {
  id: string;
  projectId: string;
  targetRepo: string;
  version: string;
  status: 'success' | 'failed';
  timestamp: Date;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  template: ProjectTemplate;
  status: ProjectStatus;
  driverConfig?: DriverConfig;
  createdAt: Date;
  updatedAt: Date;
  buildHistory: BuildRecord[];
  pushHistory: PushRecord[];
}

export interface Template {
  id: ProjectTemplate;
  name: string;
  description: string;
  icon: string;
  features: string[];
}
