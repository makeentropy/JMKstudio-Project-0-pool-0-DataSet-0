<template>
  <div class="dna-editor">
    <div class="editor-header">
      <div class="sequence-display">
        <div
          v-for="(char, index) in dnaSequence"
          :key="index"
          :class="['dna-char', char.toLowerCase()]"
        >
          {{ char }}
        </div>
        <div
          v-if="dnaSequence.length === 0"
          class="dna-placeholder"
        >
          Enter DNA sequence...
        </div>
      </div>
    </div>

    <div class="editor-controls">
      <div class="input-section">
        <label class="section-label">DNA Sequence</label>
        <input
          v-model="dnaInput"
          @input="filterInput"
          class="dna-input"
          placeholder="ATCGATCG..."
          maxlength="64"
        />
        <div class="input-hint">
          Use only A, T, C, G characters (case insensitive)
        </div>
      </div>

      <div class="action-buttons">
        <NeonButton variant="primary" @click="applySequence">
          Apply
        </NeonButton>
        <NeonButton variant="secondary" @click="clearSequence">
          Clear
        </NeonButton>
        <NeonButton variant="accent" @click="generateRandom">
          Random
        </NeonButton>
      </div>
    </div>

    <div class="dna-helix">
      <div class="helix-container">
        <div v-for="i in 16" :key="i" class="helix-rung">
          <div :class="['helix-base', bases[i % bases.length]]"></div>
          <div class="helix-bond"></div>
          <div :class="['helix-base', bases[(i + 2) % bases.length]]"></div>
        </div>
      </div>
    </div>

    <div class="sequence-stats">
      <div class="stat-item">
        <span class="stat-label">Length:</span>
        <span class="stat-value">{{ dnaSequence.length }} bp</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">A:</span>
        <span class="stat-value a">{{ countBase('A') }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">T:</span>
        <span class="stat-value t">{{ countBase('T') }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">C:</span>
        <span class="stat-value c">{{ countBase('C') }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">G:</span>
        <span class="stat-value g">{{ countBase('G') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import NeonButton from '../ui/NeonButton.vue';
import { useJMKStore } from '../../stores/jmkStore';

const store = useJMKStore();
const dnaInput = ref(store.dnaSequence);
const dnaSequence = ref(store.dnaSequence);

const bases = ['a', 't', 'c', 'g'];

watch(() => store.dnaSequence, (newSeq) => {
  dnaInput.value = newSeq;
  dnaSequence.value = newSeq;
});

function filterInput() {
  dnaInput.value = dnaInput.value.toUpperCase().replace(/[^ATCG]/g, '');
}

function applySequence() {
  if (dnaInput.value) {
    store.updateDNASequence(dnaInput.value);
    dnaSequence.value = dnaInput.value;
  }
}

function clearSequence() {
  dnaInput.value = '';
  dnaSequence.value = '';
  store.updateDNASequence('');
}

function generateRandom() {
  const length = Math.floor(Math.random() * 32) + 8;
  let sequence = '';
  for (let i = 0; i < length; i++) {
    sequence += bases[Math.floor(Math.random() * 4)].toUpperCase();
  }
  dnaInput.value = sequence;
  dnaSequence.value = sequence;
  store.updateDNASequence(sequence);
}

function countBase(base: string): number {
  return (dnaSequence.value.match(new RegExp(base, 'g')) || []).length;
}
</script>

<style scoped>
.dna-editor {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.editor-header {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(124, 58, 237, 0.2);
}

.sequence-display {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 48px;
}

.dna-char {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 700;
  border: 2px solid;
  transition: all 0.3s ease;
}

.dna-char:hover {
  transform: scale(1.1);
}

.dna-char.a {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.1);
}

.dna-char.t {
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.1);
}

.dna-char.c {
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.5);
  background: rgba(34, 197, 94, 0.1);
}

.dna-char.g {
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(59, 130, 246, 0.1);
}

.dna-placeholder {
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
}

.editor-controls {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  font-family: 'Orbitron', monospace;
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.dna-input {
  width: 100%;
  padding: 12px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  background: rgba(10, 15, 26, 0.8);
  border: 2px solid rgba(124, 58, 237, 0.3);
  border-radius: 12px;
  color: #a78bfa;
  outline: none;
  transition: all 0.3s ease;
}

.dna-input:focus {
  border-color: rgba(124, 58, 237, 0.6);
  box-shadow: 0 0 20px rgba(124, 58, 237, 0.2);
}

.input-hint {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #64748b;
}

.action-buttons {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.dna-helix {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.helix-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.helix-rung {
  display: flex;
  align-items: center;
  gap: 8px;
}

.helix-base {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  transition: all 0.5s ease;
}

.helix-base.a {
  background: #ef4444;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
}

.helix-base.t {
  background: #f59e0b;
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
}

.helix-base.c {
  background: #22c55e;
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
}

.helix-base.g {
  background: #3b82f6;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
}

.helix-bond {
  width: 40px;
  height: 3px;
  background: linear-gradient(90deg, #7c3aed, #06b6d4);
  border-radius: 2px;
}

.sequence-stats {
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
  padding: 16px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-family: 'Orbitron', monospace;
  font-size: 0.75rem;
  color: #64748b;
}

.stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  font-weight: 700;
  color: #e2e8f0;
}

.stat-value.a { color: #ef4444; }
.stat-value.t { color: #f59e0b; }
.stat-value.c { color: #22c55e; }
.stat-value.g { color: #3b82f6; }

@media (max-width: 768px) {
  .editor-controls {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    width: 100%;
  }
}
</style>
