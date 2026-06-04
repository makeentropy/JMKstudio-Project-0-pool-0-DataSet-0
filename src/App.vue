<template>
  <div class="app">
    <Navbar />
    <main class="main-content">
      <Dashboard v-if="store.currentPage === 'dashboard'" />
      <DNAConfigEditor v-else-if="store.currentPage === 'dna-config'" />
      <DimensionManager v-else-if="store.currentPage === 'dimension-manager'" />
      <TerminalShell v-else-if="store.currentPage === 'terminal'" />
    </main>
  </div>
</template>

<script setup lang="ts">
import Navbar from './components/ui/Navbar.vue';
import Dashboard from './pages/Dashboard.vue';
import DNAConfigEditor from './pages/DNAConfigEditor.vue';
import DimensionManager from './pages/DimensionManager.vue';
import TerminalShell from './pages/TerminalShell.vue';
import { useJMKStore } from './stores/jmkStore';

const store = useJMKStore();
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #0a0f1a;
  color: #e2e8f0;
  overflow-x: hidden;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
}
</style>
