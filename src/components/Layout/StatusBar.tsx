import { motion } from 'framer-motion';
import { Activity, Clock, Server, HardDrive } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';

export function StatusBar() {
  const { projects, buildLogs } = useProjectStore();

  const activeBuilds = projects.filter(p => p.status === 'building').length;
  const activePushes = projects.filter(p => p.status === 'pushing').length;
  const totalBuilds = projects.reduce((acc, p) => acc + p.buildHistory.length, 0);

  return (
    <footer className="h-10 bg-[#0a0e17]/90 backdrop-blur-md border-t border-[#00d4ff]/10 flex items-center justify-between px-4 text-xs">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 text-[#94a3b8]">
          <Server className="w-3 h-3" />
          <span>项目: <span className="text-[#00d4ff]">{projects.length}</span></span>
        </div>
        <div className="flex items-center gap-1.5 text-[#94a3b8]">
          <Activity className="w-3 h-3" />
          <span>构建中: <span className={activeBuilds > 0 ? 'text-[#ff6b35]' : 'text-[#94a3b8]'}>
            {activeBuilds}
          </span></span>
        </div>
        <div className="flex items-center gap-1.5 text-[#94a3b8]">
          <HardDrive className="w-3 h-3" />
          <span>推送中: <span className={activePushes > 0 ? 'text-[#a855f7]' : 'text-[#94a3b8]'}>
            {activePushes}
          </span></span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {buildLogs.length > 0 && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-1.5"
          >
            <div className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
            <span className="text-[#10b981]">构建日志: {buildLogs.length} 条</span>
          </motion.div>
        )}
        <div className="flex items-center gap-1.5 text-[#94a3b8]">
          <Clock className="w-3 h-3" />
          <span>累计构建: <span className="text-[#f1f5f9]">{totalBuilds}</span></span>
        </div>
      </div>
    </footer>
  );
}
