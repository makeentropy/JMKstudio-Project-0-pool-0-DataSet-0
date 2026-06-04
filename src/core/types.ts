export interface EntropyDNANode {
  id: string;
  base: 'A' | 'T' | 'C' | 'G';
  entropy: number;
  timestamp: number;
  dimension: number;
}

export interface CausalEvent {
  id: string;
  timestamp: number;
  timeline: number;
  karma: number;
  payload: any;
  spaceBranch: 'Parallel_A' | 'Parallel_B';
}

export interface EventPayload {
  type: string;
  data: any;
  metadata?: Record<string, any>;
}

export interface ParallelSpaceData {
  timestamp: number;
  karma: number;
  payload: any;
  spaceBranch: 'Parallel_A' | 'Parallel_B';
}

export interface JMKmapNode {
  id: string;
  x: number;
  y: number;
  angle: number;
  radius: number;
  entropy: number;
  label: string;
}
