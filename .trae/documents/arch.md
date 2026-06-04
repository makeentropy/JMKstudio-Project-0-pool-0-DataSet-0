
## 1. Architecture Design
```mermaid
graph TB
    subgraph "观测层 (Frontend)"
        A1[3D Space Viewer<br/>Vue + Three.js]
        A2[JMKmap Spiral<br/>D3.js + ECharts]
        A3[DNA Config Editor<br/>Vue Component]
        A4[Gene Terminal<br/>xterm.js]
    end
    
    subgraph "节律层 (JS Agent)"
        B1[Karma Rhythm Controller]
        B2[Event Control Framework]
        B3[Time Causal Increment]
    end
    
    subgraph "基底内核层 (Core)"
        C1[base_XOR_boost-kernel]
        C2[Dataset Pool Manager]
        C3[System Log Engine]
    end
    
    subgraph "奇点内存层 (Data)"
        D1[Quantum Singularity Space]
        D2[Entropy DNA Storage]
        D3[Parallel Space Branches]
    end
    
    A1 --&gt; B1
    A2 --&gt; B1
    A3 --&gt; B2
    A4 --&gt; B3
    B1 --&gt; C1
    B2 --&gt; C2
    B3 --&gt; C3
    C1 --&gt; D1
    C2 --&gt; D2
    C3 --&gt; D3
```

## 2. Technology Description
- Frontend: Vue@3 + TypeScript + Vite + TailwindCSS
- 3D Rendering: Three.js + @react-three/fiber (备选) + D3.js
- Terminal: xterm.js
- State Management: Pinia (Vue) / Zustand (React 备选)
- Backend: Express.js (可选，用于数据集存储)
- Database: LocalStorage (Client-side) + File-based (Server-side)

## 3. Route Definitions
| Route | Purpose |
|-------|---------|
| / | Dashboard - 3D空间全景 |
| /singularity | Quantum Singularity View |
| /dna-config | DNA Config Editor |
| /dimension-manager | Dimension Manager Admin |
| /terminal | Gene Terminal Shell |

## 4. Core Data Structures

### 4.1 QuantumSingularity
```typescript
class QuantumSingularity {
  JMKmap_Pi: number;
  entropyDNA: EntropyDNANode[];
  causalLog: CausalEvent[];
  
  constructor();
  runSingularityAlgorithm(dimensions: number[]): number[];
  calculateEntropy(): number;
}
```

### 4.2 KarmaRhythmController
```typescript
class KarmaRhythmController {
  dna: string;
  timeline: number;
  
  constructor(dnaSequence: string);
  triggerCausalEvent(eventPayload: EventPayload): void;
  calculateKarmaFactor(payload: EventPayload): number;
  commitToParallelSpace(data: ParallelSpaceData): void;
}
```

### 4.3 DimensionManager
```typescript
class DimensionManager {
  spatialPassword: string;
  hiddenDataLayer: Map&lt;string, boolean&gt;;
  
  constructor(spatialPassword: string);
  hideDataInPlainText(plainTextDNA: string, sensitiveData: any): string;
  retrieveTopology(cipherDNA: string): any;
  xorBoostKernel(plain: string, data: any, password: string): string;
}
```

## 5. File Structure
```
/workspace
├── src/
│   ├── components/
│   │   ├── 3d/
│   │   │   ├── StringNetwork.vue
│   │   │   ├── SingularityCore.vue
│   │   │   └── JMKmapSpiral.vue
│   │   ├── dna/
│   │   │   ├── DNASequenceEditor.vue
│   │   │   └── DNASpiralScroll.vue
│   │   ├── terminal/
│   │   │   └── GeneTerminal.vue
│   │   └── ui/
│   │       ├── GlassCard.vue
│   │       └── NeonButton.vue
│   ├── pages/
│   │   ├── Dashboard.vue
│   │   ├── QuantumSingularityView.vue
│   │   ├── DNAConfigEditor.vue
│   │   ├── DimensionManager.vue
│   │   └── TerminalShell.vue
│   ├── composables/
│   │   ├── useQuantumSingularity.ts
│   │   ├── useKarmaRhythm.ts
│   │   └── useDimensionManager.ts
│   ├── core/
│   │   ├── QuantumSingularity.ts
│   │   ├── KarmaRhythmController.ts
│   │   └── DimensionManager.ts
│   ├── utils/
│   │   ├── dnaUtils.ts
│   │   ├── mathUtils.ts
│   │   └── entropyUtils.ts
│   ├── App.vue
│   └── main.ts
├── api/ (optional backend)
│   └── dataset-pool/
├── public/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.js
```
