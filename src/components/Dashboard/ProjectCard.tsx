import { motion } from 'framer-motion';
import { Database, Brain, GitBranch, HardDrive, Sparkles, Trash2, MoreVertical } from 'lucide-react';
import type { Project } from '../../types';
import { useProjectStore } from '../../store/projectStore';

const iconMap: Record<string, typeof Database> = {
  'dataset-builder': Database,
  'model-training': Brain,
  'pipeline': GitBranch,
  'xor-pool': HardDrive,
  'custom': Sparkles,
};

const statusColors: Record<string, string> = {
  idle: 'border-[#94a3b8]/30 bg-[#94a3b8]/5',
  generating: 'border-[#a855f7]/30 bg-[#a855f7]/5',
  coding: 'border-[#00d4ff]/30 bg-[#00d4ff]/5',
  building: 'border-[#ff6b35]/30 bg-[#ff6b35]/5',
  pushing: 'border-[#a855f7]/30 bg-[#a855f7]/5',
  completed: 'border-[#10b981]/30 bg-[#10b981]/5',
  error: 'border-[#ef4444]/30 bg-[#ef4444]/5',
};

const statusTextColors: Record<string, string> = {
  idle: 'text-[#94a3b8]',
  generating: 'text-[#a855f7]',
  coding: 'text-[#00d4ff]',
  building: 'text-[#ff6b35]',
  pushing: 'text-[#a855f7]',
  completed: 'text-[#10b981]',
  error: 'text-[#ef4444]',
};

interface ProjectCardProps {
  project: Project;
  index: number;
}

export function ProjectCard({ project, index }: ProjectCardProps) {
  const { deleteProject, setCurrentProject } = useProjectStore();
  const Icon = iconMap[project.template] || Sparkles;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className={`relative p-5 rounded-2xl border backdrop-blur-sm cursor-pointer overflow-hidden ${statusColors[project.status]}`}
      whileHover={{ scale: 1.02, y: -4 }}
      onClick={() => setCurrentProject(project)}
    >
      {/* Glow effect */}
      <div className={`absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-500 ${
        project.status === 'building' ? 'bg-gradient-to-br from-[#ff6b35]/5 to-transparent' :
        project.status === 'completed' ? 'bg-gradient-to-br from-[#10b981]/5 to-transparent' :
        'bg-gradient-to-br from-[#00d4ff]/5 to-transparent'
      }`} />

      {/* Background pattern */}
      <div className="absolute inset-0 opacity-[0.02]" style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%2300d4ff' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
      }} />

      <div className="relative z-10">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <motion.div
              className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] flex items-center justify-center border border-[#00d4ff]/20"
              whileHover={{ rotate: 5, scale: 1.05 }}
            >
              <Icon className="w-6 h-6 text-[#00d4ff]" />
            </motion.div>
            <div>
              <h3 className="text-base font-bold text-[#f1f5f9]">{project.name}</h3>
              <p className="text-xs text-[#94a3b8] mt-0.5">{project.description}</p>
            </div>
          </div>
          <motion.button
            onClick={(e) => {
              e.stopPropagation();
              deleteProject(project.id);
            }}
            className="p-2 rounded-lg hover:bg-[#ef4444]/10 text-[#94a3b8] hover:text-[#ef4444] transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <Trash2 className="w-4 h-4" />
          </motion.button>
        </div>

        <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#00d4ff]/10">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full bg-[#1a1a2e] border border-current/20 ${statusTextColors[project.status]}`}>
              {project.status === 'idle' && '空闲'}
              {project.status === 'generating' && '生成中'}
              {project.status === 'coding' && '编码中'}
              {project.status === 'building' && '构建中'}
              {project.status === 'pushing' && '推送中'}
              {project.status === 'completed' && '已完成'}
              {project.status === 'error' && '错误'}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-[#94a3b8]">
            <span>{project.buildHistory.length} 构建</span>
            <span>{project.pushHistory.length} 推送</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
