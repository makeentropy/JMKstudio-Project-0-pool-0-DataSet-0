import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project, ViewType, BuildRecord, PushRecord } from '../types';

interface ProjectStore {
  projects: Project[];
  currentProject: Project | null;
  activeView: ViewType;
  buildLogs: string[];

  addProject: (project: Project) => void;
  updateProject: (id: string, updates: Partial<Project>) => void;
  deleteProject: (id: string) => void;
  setCurrentProject: (project: Project | null) => void;
  setActiveView: (view: ViewType) => void;
  addBuildRecord: (projectId: string, record: BuildRecord) => void;
  addPushRecord: (projectId: string, record: PushRecord) => void;
  appendBuildLog: (log: string) => void;
  clearBuildLogs: () => void;
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      projects: [],
      currentProject: null,
      activeView: 'dashboard',
      buildLogs: [],

      addProject: (project) =>
        set((state) => ({ projects: [...state.projects, project] })),

      updateProject: (id, updates) =>
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === id ? { ...p, ...updates, updatedAt: new Date() } : p
          ),
        })),

      deleteProject: (id) =>
        set((state) => ({
          projects: state.projects.filter((p) => p.id !== id),
          currentProject:
            state.currentProject?.id === id ? null : state.currentProject,
        })),

      setCurrentProject: (project) => set({ currentProject: project }),

      setActiveView: (view) => set({ activeView: view }),

      addBuildRecord: (projectId, record) =>
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === projectId
              ? {
                  ...p,
                  buildHistory: [...p.buildHistory, record],
                  status: record.status === 'in-progress' ? 'building' : record.status === 'success' ? 'completed' : 'error',
                }
              : p
          ),
        })),

      addPushRecord: (projectId, record) =>
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === projectId
              ? {
                  ...p,
                  pushHistory: [...p.pushHistory, record],
                  status: record.status === 'success' ? 'completed' : 'error',
                }
              : p
          ),
        })),

      appendBuildLog: (log) =>
        set((state) => ({ buildLogs: [...state.buildLogs, log] })),

      clearBuildLogs: () => set({ buildLogs: [] }),
    }),
    {
      name: 'datasci-projecter-storage',
    }
  )
);
