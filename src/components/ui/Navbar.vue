<template>
  <nav class="navbar">
    <div class="navbar-container">
      <div class="navbar-logo" @click="navigateTo('dashboard')">
        <span class="logo-icon">⚡</span>
        <span class="logo-text">JMK-Dimension</span>
      </div>

      <div class="navbar-links">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigateTo(item.path)"
          :class="['nav-link', { active: currentPath === item.path }]"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </div>

      <div class="navbar-status">
        <div class="status-dot"></div>
        <span class="status-text">System Online</span>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useJMKStore } from '../../stores/jmkStore';

const store = useJMKStore();

const currentPath = computed(() => store.currentPage);

const navItems = [
  { path: 'dashboard', label: 'Dashboard', icon: '📊' },
  { path: 'dna-config', label: 'DNA Config', icon: '🧬' },
  { path: 'dimension-manager', label: 'Dimension Manager', icon: '🌌' },
  { path: 'terminal', label: 'Terminal', icon: '💻' }
];

function navigateTo(path: string) {
  store.setPage(path);
}
</script>

<style scoped>
.navbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(124, 58, 237, 0.2);
}

.navbar-container {
  max-width: 1800px;
  margin: 0 auto;
  padding: 0 32px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: opacity 0.3s ease;
}

.navbar-logo:hover {
  opacity: 0.8;
}

.logo-icon {
  font-size: 2rem;
}

.logo-text {
  font-family: 'Orbitron', monospace;
  font-size: 1.25rem;
  font-weight: 900;
  background: linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.navbar-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: transparent;
  border: none;
  border-radius: 12px;
  color: #94a3b8;
  font-family: 'Orbitron', monospace;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.nav-link:hover {
  background: rgba(124, 58, 237, 0.1);
  color: #e2e8f0;
}

.nav-link.active {
  background: rgba(124, 58, 237, 0.2);
  color: #a78bfa;
  border: 1px solid rgba(124, 58, 237, 0.3);
}

.nav-icon {
  font-size: 1.125rem;
}

.navbar-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #22c55e;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4);
  }
  50% {
    opacity: 0.8;
    box-shadow: 0 0 0 8px rgba(34, 197, 94, 0);
  }
}

.status-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  color: #22c55e;
}

@media (max-width: 768px) {
  .navbar-container {
    padding: 0 16px;
    height: auto;
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }

  .navbar-links {
    flex-wrap: wrap;
    justify-content: center;
  }

  .nav-label {
    display: none;
  }
}
</style>
