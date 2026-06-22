import { motion } from 'framer-motion';
import { FolderKanban, ChevronRight, Database, Brain, GitBranch, HardDrive, Sparkles } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';

const iconMap: Record<string, typeof Database> = {
  'dataset-builder': Database,
  'model-training': Brain,
  'pipeline': GitBranch,
  'xor-pool': HardDrive,
  'custom': Sparkles,
};

const statusColors: Record<string, string> = {
  idle: 'bg-[#94a3b8]',
  generating: 'bg-[#a855f7]',
  coding: 'bg-[#00d4ff]',
  building: 'bg-[#ff6b35]',
  pushing: 'bg-[#a855f7]',
  completed: 'bg-[#10b981]',
  error: 'bg-[#ef4444]',
};

export function Sidebar() {
  const { projects, currentProject, setCurrentProject } = useProjectStore();

  return (
    <aside className="w-64 bg-[#0a0e17]/50 border-r border-[#00d4ff]/10 flex flex-col">
      <div className="p-4 border-b border-[#00d4ff]/10">
        <div className="flex items-center gap-2 text-[#94a3b8]">
          <FolderKanban className="w-4 h-4" />
          <span className="text-sm font-medium">项目列表</span>
          <span className="ml-auto text-xs bg-[#00d4ff]/20 text-[#00d4ff] px-2 py-0.5 rounded-full">
            {projects.length}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {projects.length === 0 ? (
          <div className="text-center py-8 text-[#94a3b8]/60">
            <FolderKanban className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-xs">暂无项目</p>
            <p className="text-xs text-[#94a3b8]/40">点击"生成项目"创建</p>
          </div>
        ) : (
          projects.map((project) => {
            const Icon = iconMap[project.template] || Sparkles;
            const isSelected = currentProject?.id === project.id;

            return (
              <motion.button
                key={project.id}
                onClick={() => setCurrentProject(project)}
                className={`w-full p-3 rounded-lg flex items-center gap-3 transition-colors ${
                  isSelected
                    ? 'bg-[#00d4ff]/10 border border-[#00d4ff]/30'
                    : 'hover:bg-[#1a1a2e]/50 border border-transparent'
                }`}
                whileHover={{ x: 4 }}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  isSelected
                    ? 'bg-[#00d4ff]/20'
                    : 'bg-[#1a1a2e]'
                }`}>
                  <Icon className={`w-4 h-4 ${
                    isSelected ? 'text-[#00d4ff]' : 'text-[#94a3b8]'
                  }`} />
                </div>
                <div className="flex-1 text-left min-w-0">
                  <p className={`text-sm font-medium truncate ${
                    isSelected ? 'text-[#f1f5f9]' : 'text-[#94a3b8]'
                  }`}>
                    {project.name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div className={`w-1.5 h-1.5 rounded-full ${statusColors[project.status]}`} />
                    <span className="text-[10px] text-[#94a3b8]/60 capitalize">
                      {project.status}
                    </span>
                  </div>
                </div>
                <ChevronRight className={`w-4 h-4 ${
                  isSelected ? 'text-[#00d4ff]' : 'text-[#94a3b8]/30'
                }`} />
              </motion.button>
            );
          })
        )}
      </div>
    </aside>
  );
}
