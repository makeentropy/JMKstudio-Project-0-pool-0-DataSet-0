import { motion } from 'framer-motion';
import { FolderKanban } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';
import { ProjectCard } from './ProjectCard';
import { StatsPanel } from './StatsPanel';

export function ProjectDashboard() {
  const { projects } = useProjectStore();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#f1f5f9]">项目仪表盘</h2>
          <p className="text-sm text-[#94a3b8] mt-1">管理所有数据科学工程项目</p>
        </div>
      </div>

      <StatsPanel />

      {projects.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex flex-col items-center justify-center py-20 rounded-2xl bg-gradient-to-br from-[#1a1a2e]/50 to-[#16213e]/50 border border-dashed border-[#00d4ff]/20"
        >
          <div className="w-20 h-20 rounded-2xl bg-[#1a1a2e] flex items-center justify-center mb-4">
            <FolderKanban className="w-10 h-10 text-[#94a3b8]/50" />
          </div>
          <h3 className="text-lg font-medium text-[#f1f5f9] mb-2">暂无项目</h3>
          <p className="text-sm text-[#94a3b8] mb-4">点击左侧"生成项目"创建你的第一个项目</p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {projects.map((project, index) => (
            <ProjectCard key={project.id} project={project} index={index} />
          ))}
        </div>
      )}
    </motion.div>
  );
}
