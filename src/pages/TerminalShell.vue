<template>
  <div class="terminal-page">
    <div class="terminal-header">
      <div class="terminal-dots">
        <div class="dot dot-red"></div>
        <div class="dot dot-yellow"></div>
        <div class="dot dot-green"></div>
      </div>
      <div class="terminal-title">JMK-CAUSAL:~</div>
    </div>

    <div class="terminal-body" ref="terminalBody" @click="focusInput">
      <div class="terminal-output" ref="outputRef">
        <div class="terminal-line">
          <span class="timestamp">[{{ formatTime(initTime) }}]</span>
          <span class="system-text">System initialized. Welcome to JMK-Dimension Studio.</span>
        </div>
        <div class="terminal-line">
          <span class="timestamp">[{{ formatTime(initTime) }}]</span>
          <span class="system-text">JMKmap_Pi = {{ pi.toFixed(8) }}</span>
        </div>
        <div class="terminal-line">
          <span class="timestamp">[{{ formatTime(initTime) }}]</span>
          <span class="system-text">Type 'help' for available commands.</span>
        </div>

        <div
          v-for="(entry, index) in commandHistory"
          :key="index"
          class="terminal-line"
        >
          <span class="timestamp">[{{ formatTime(entry.timestamp) }}]</span>
          <span class="prompt">user@jmk:~$</span>
          <span class="command-text">{{ entry.command }}</span>
          <div v-if="entry.output" class="command-output">
            <pre>{{ entry.output }}</pre>
          </div>
          <div v-if="entry.event" class="causal-event">
            <span :class="['event-type', entry.event.spaceBranch.toLowerCase()]">
              [{{ entry.event.spaceBranch }}]
            </span>
            <span class="event-karma">Karma: {{ entry.event.karma.toFixed(4) }}</span>
          </div>
        </div>
      </div>

      <div class="terminal-input-line">
        <span class="timestamp">[{{ formatTime(Date.now()) }}]</span>
        <span class="prompt">user@jmk:~$</span>
        <input
          ref="inputRef"
          v-model="currentCommand"
          @keydown.enter="executeCommand"
          @keydown.up="historyUp"
          @keydown.down="historyDown"
          class="terminal-input"
          type="text"
          autocomplete="off"
          placeholder="Enter command..."
        />
        <span class="cursor" :class="{ visible: inputFocused }"></span>
      </div>
    </div>

    <div class="terminal-status">
      <div class="status-item">
        <span class="status-label">Timeline</span>
        <span class="status-value timeline">{{ store.timeline }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">Entropy</span>
        <span class="status-value entropy">{{ store.entropy.toFixed(4) }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">Events</span>
        <span class="status-value">{{ store.causalEvents.length }}</span>
      </div>
      <div class="status-item">
        <span class="status-label">DNA</span>
        <span class="status-value">{{ store.dnaSequence.length }}bp</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue';
import { useJMKStore } from '../stores/jmkStore';

const store = useJMKStore();
const pi = Math.PI;
const initTime = Date.now();

const terminalBody = ref<HTMLElement | null>(null);
const outputRef = ref<HTMLElement | null>(null);
const inputRef = ref<HTMLInputElement | null>(null);
const currentCommand = ref('');
const commandHistory = ref<Array<{
  command: string;
  timestamp: number;
  output?: string;
  event?: any;
}>>([]);
const historyIndex = ref(-1);
const inputFocused = ref(false);

const commands = {
  help: () => {
    return `Available commands:
  help              - Show this help
  status            - Show system status
  trigger <type>    - Trigger causal event (types: create, update, delete, query)
  dna <sequence>    - Update DNA sequence
  entropy           - Calculate current entropy
  timeline          - Show timeline events
  clear             - Clear terminal
  reset             - Reset singularity state`;
  },
  status: () => {
    return `System Status:
  Timeline: ${store.timeline}
  Entropy: ${store.entropy.toFixed(4)}
  Causal Events: ${store.causalEvents.length}
  Parallel Space Data: ${store.parallelSpaceData.length} items
  DNA Length: ${store.dnaSequence.length} bp`;
  },
  trigger: (args: string[]) => {
    const type = args[0] || 'update';
    const event = store.triggerEvent(type, { source: 'terminal' });
    return { event };
  },
  dna: (args: string[]) => {
    const seq = args[0]?.toUpperCase() || '';
    if (!/^[ATCG]*$/.test(seq)) {
      return 'Error: DNA sequence can only contain A, T, C, G';
    }
    store.updateDNASequence(seq || 'ATCGATCG');
    return `DNA sequence updated: ${store.dnaSequence}`;
  },
  entropy: () => {
    return `Current Entropy: ${store.entropy.toFixed(6)}`;
  },
  timeline: () => {
    const events = store.causalEvents.slice(0, 10);
    if (events.length === 0) return 'No events in timeline';
    return events.map(e =>
      `[${new Date(e.timestamp).toLocaleTimeString()}] ${e.spaceBranch} - Karma: ${e.karma.toFixed(4)}`
    ).join('\n');
  },
  clear: () => {
    commandHistory.value = [];
    return null;
  },
  reset: () => {
    store.reset();
    return 'Singularity reset complete';
  }
};

function executeCommand() {
  const cmd = currentCommand.value.trim();
  if (!cmd) return;

  const timestamp = Date.now();
  const parts = cmd.split(/\s+/);
  const commandName = parts[0].toLowerCase();
  const args = parts.slice(1);

  let result: any;

  if (commands[commandName as keyof typeof commands]) {
    result = (commands[commandName as keyof typeof commands] as any)(args);
  } else {
    result = `Command not found: ${commandName}. Type 'help' for available commands.`;
  }

  if (result !== null) {
    const historyEntry: any = {
      command: cmd,
      timestamp
    };
    if (typeof result === 'string') {
      historyEntry.output = result;
    } else if (result.event) {
      historyEntry.output = `Event triggered: ${result.event.payload.type}`;
      historyEntry.event = result.event;
    }
    commandHistory.value.push(historyEntry);
  }

  currentCommand.value = '';
  historyIndex.value = -1;

  nextTick(() => scrollToBottom());
}

function historyUp() {
  if (commandHistory.value.length === 0) return;
  if (historyIndex.value < commandHistory.value.length - 1) {
    historyIndex.value++;
    currentCommand.value = commandHistory.value[commandHistory.value.length - 1 - historyIndex.value].command;
  }
}

function historyDown() {
  if (historyIndex.value > 0) {
    historyIndex.value--;
    currentCommand.value = commandHistory.value[commandHistory.value.length - 1 - historyIndex.value].command;
  } else if (historyIndex.value === 0) {
    historyIndex.value = -1;
    currentCommand.value = '';
  }
}

function focusInput() {
  inputRef.value?.focus();
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString();
}

function scrollToBottom() {
  if (terminalBody.value) {
    terminalBody.value.scrollTop = terminalBody.value.scrollHeight;
  }
}

onMounted(() => {
  focusInput();
});

watch(() => store.entropy, () => {
  scrollToBottom();
});
</script>

<style scoped>
.terminal-page {
  min-height: 100vh;
  background: #0a0f1a;
  display: flex;
  flex-direction: column;
}

.terminal-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: rgba(30, 41, 59, 0.8);
  border-bottom: 1px solid rgba(124, 58, 237, 0.2);
}

.terminal-dots {
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot-red {
  background: #ef4444;
}

.dot-yellow {
  background: #f59e0b;
}

.dot-green {
  background: #22c55e;
}

.terminal-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  color: #94a3b8;
}

.terminal-body {
  flex: 1;
  padding: 24px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  overflow-y: auto;
  background: #020617;
}

.terminal-body::-webkit-scrollbar {
  width: 8px;
}

.terminal-body::-webkit-scrollbar-track {
  background: rgba(10, 15, 26, 0.5);
}

.terminal-body::-webkit-scrollbar-thumb {
  background: rgba(124, 58, 237, 0.5);
  border-radius: 4px;
}

.terminal-output {
  margin-bottom: 16px;
}

.terminal-line {
  margin-bottom: 8px;
  line-height: 1.6;
}

.timestamp {
  color: #64748b;
  margin-right: 8px;
}

.prompt {
  color: #a78bfa;
  font-weight: 700;
  margin-right: 8px;
}

.system-text {
  color: #67e8f9;
}

.command-text {
  color: #e2e8f0;
}

.command-output {
  margin-left: 40px;
  margin-top: 4px;
  color: #94a3b8;
}

.command-output pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
}

.causal-event {
  margin-left: 40px;
  margin-top: 4px;
  display: flex;
  gap: 16px;
}

.event-type {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.75rem;
}

.event-type.parallel_a {
  background: rgba(124, 58, 237, 0.2);
  color: #a78bfa;
}

.event-type.parallel_b {
  background: rgba(6, 182, 212, 0.2);
  color: #67e8f9;
}

.event-karma {
  color: #22c55e;
}

.terminal-input-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  color: #e2e8f0;
}

.cursor {
  width: 8px;
  height: 16px;
  background: #a78bfa;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.cursor.visible {
  opacity: 1;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.terminal-status {
  display: flex;
  gap: 32px;
  padding: 16px 24px;
  background: rgba(30, 41, 59, 0.8);
  border-top: 1px solid rgba(124, 58, 237, 0.2);
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font-family: 'Orbitron', monospace;
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #64748b;
}

.status-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.125rem;
  font-weight: 700;
  color: #e2e8f0;
}

.status-value.timeline {
  color: #a78bfa;
}

.status-value.entropy {
  color: #67e8f9;
}
</style>
