import type { EventPayload, ParallelSpaceData, CausalEvent } from './types';
import { QuantumSingularity } from './QuantumSingularity';

export class KarmaRhythmController {
  dna: string;
  timeline: number;
  private singularity: QuantumSingularity;
  private parallelSpaceData: ParallelSpaceData[];

  constructor(dnaSequence: string, singularity: QuantumSingularity) {
    this.dna = dnaSequence;
    this.timeline = 0;
    this.singularity = singularity;
    this.parallelSpaceData = [];
  }

  triggerCausalEvent(eventPayload: EventPayload): CausalEvent {
    this.timeline += 1;
    const karmaFactor = this.calculateKarmaFactor(eventPayload);
    const spaceBranch = karmaFactor > 0.5 ? 'Parallel_A' : 'Parallel_B';

    const event: CausalEvent = {
      id: 'event-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9),
      timestamp: Date.now(),
      timeline: this.timeline,
      karma: karmaFactor,
      payload: eventPayload,
      spaceBranch
    };

    this.commitToParallelSpace({
      timestamp: event.timestamp,
      karma: karmaFactor,
      payload: eventPayload,
      spaceBranch
    });

    this.singularity.addCausalEvent(event);

    const bases: ('A' | 'T' | 'C' | 'G')[] = ['A', 'T', 'C', 'G'];
    this.singularity.addEntropyDNANode(
      bases[Math.floor(Math.random() * 4)],
      Math.floor(karmaFactor * 4)
    );

    return event;
  }

  calculateKarmaFactor(payload: EventPayload): number {
    const dnaHash = this.hashDNA(this.dna);
    const payloadHash = this.hashPayload(payload);
    const combined = (dnaHash + payloadHash) % 1000;
    return (Math.sin(combined * 0.01) + 1) / 2;
  }

  commitToParallelSpace(data: ParallelSpaceData): void {
    this.parallelSpaceData.push(data);
    if (this.parallelSpaceData.length > 50) {
      this.parallelSpaceData.shift();
    }
    try {
      const existing = localStorage.getItem('jmk-dataset-pool');
      const dataset = existing ? JSON.parse(existing) : [];
      dataset.push({ ...data, savedAt: Date.now() });
      localStorage.setItem('jmk-dataset-pool', JSON.stringify(dataset.slice(-200)));
    } catch (e) {
      console.warn('Failed to save to dataset pool:', e);
    }
  }

  private hashDNA(dna: string): number {
    let hash = 0;
    for (let i = 0; i < dna.length; i++) {
      const char = dna.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  private hashPayload(payload: EventPayload): number {
    const str = JSON.stringify(payload);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  getParallelSpaceData(): ParallelSpaceData[] {
    return [...this.parallelSpaceData];
  }

  updateDNA(newDna: string): void {
    this.dna = newDna;
  }
}
