
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/pages/Dashboard.vue'
import DNAConfigEditor from '@/pages/DNAConfigEditor.vue'
import DimensionManager from '@/pages/DimensionManager.vue'
import TerminalShell from '@/pages/TerminalShell.vue'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: Dashboard,
  },
  {
    path: '/dna-config',
    name: 'dna-config',
    component: DNAConfigEditor,
  },
  {
    path: '/dimension-manager',
    name: 'dimension-manager',
    component: DimensionManager,
  },
  {
    path: '/terminal',
    name: 'terminal',
    component: TerminalShell,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
