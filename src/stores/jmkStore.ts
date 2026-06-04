import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { QuantumSingularity } from '../core/QuantumSingularity';
import { KarmaRhythmController } from '../core/KarmaRhythmController';
import { DimensionManager } from '../core/DimensionManager';

export const useJMKStore = defineStore('jmk', () => {
  // 用普通变量存储实例，不放入响应式系统
  let singularity = new QuantumSingularity();
  let karmaController = new KarmaRhythmController('ATCGATCGATCGATCG', singularity);
  let dimensionManager = new DimensionManager('JMK-DIMENSION-KEY');

  const currentPage = ref('dashboard');
  const isRunning = ref(false);
  const spatialPassword = ref('JMK-DIMENSION-KEY');
  const dnaSequence = ref('ATCGATCGATCGATCG');
  const refreshTrigger = ref(0);

  const entropy = computed(() => {
    refreshTrigger.value;
    return singularity.calculateEntropy();
  });
  const timeline = computed(() => {
    refreshTrigger.value;
    return karmaController.timeline;
  });
  const causalEvents = computed(() => {
    refreshTrigger.value;
    return [...singularity.causalLog].reverse();
  });
  const parallelSpaceData = computed(() => {
    refreshTrigger.value;
    return karmaController.getParallelSpaceData();
  });
  const entropyDNA = computed(() => {
    refreshTrigger.value;
    return singularity.entropyDNA;
  });
  const jmkNodes = computed(() => {
    refreshTrigger.value;
    return singularity.getJMKmapNodes(32);
  });

  function refresh() {
    refreshTrigger.value++;
  }

  function triggerEvent(type: string, data: any = {}) {
    const result = karmaController.triggerCausalEvent({
      type,
      data,
      metadata: { timestamp: Date.now() }
    });
    refresh();
    return result;
  }

  function updateDNASequence(newSequence: string) {
    dnaSequence.value = newSequence;
    karmaController.updateDNA(newSequence);
    refresh();
  }

  function updateSpatialPassword(newPassword: string) {
    spatialPassword.value = newPassword;
    dimensionManager.updatePassword(newPassword);
    refresh();
  }

  function hideData(plainText: string, data: any) {
    const result = dimensionManager.hideDataInPlainText(plainText, data);
    refresh();
    return result;
  }

  function retrieveData(cipher: string) {
    return dimensionManager.retrieveTopology(cipher);
  }

  function setPage(page: string) {
    currentPage.value = page;
  }

  function toggleRunning() {
    isRunning.value = !isRunning.value;
  }

  function reset() {
    singularity = new QuantumSingularity();
    karmaController = new KarmaRhythmController(dnaSequence.value, singularity);
    dimensionManager = new DimensionManager(spatialPassword.value);
    refresh();
  }

  return {
    get singularity() { return singularity; },
    get karmaController() { return karmaController; },
    get dimensionManager() { return dimensionManager; },
    currentPage,
    isRunning,
    spatialPassword,
    dnaSequence,
    entropy,
    timeline,
    causalEvents,
    parallelSpaceData,
    entropyDNA,
    jmkNodes,
    triggerEvent,
    updateDNASequence,
    updateSpatialPassword,
    hideData,
    retrieveData,
    setPage,
    toggleRunning,
    reset
  };
});
