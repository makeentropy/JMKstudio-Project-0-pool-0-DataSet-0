import { useState } from 'react';
import { motion } from 'framer-motion';
import { Hammer, Loader2, FolderKanban, AlertCircle } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';
import { BuildConsole } from './BuildConsole';
import { BuildHistory } from './BuildHistory';
import type { BuildRecord } from '../../types';

const buildSteps = [
  { label: '安装依赖', duration: 800 },
  { label: '编译源码', duration: 1200 },
  { label: '运行测试', duration: 600 },
  { label: '打包产物', duration: 400 },
];

export function ProjectBuilder() {
  const { currentProject, updateProject, addBuildRecord, appendBuildLog, clearBuildLogs } = useProjectStore();
  const [isBuilding, setIsBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useState(0);

  const simulateBuild = async () => {
    if (!currentProject) return;

    setIsBuilding(true);
    setBuildProgress(0);
    clearBuildLogs();

    const buildId = `build_${Date.now()}`;
    const record: BuildRecord = {
      id: buildId,
      projectId: currentProject.id,
      status: 'in-progress',
      logs: '',
      duration: 0,
      artifacts: [],
      timestamp: new Date(),
    };

    addBuildRecord(currentProject.id, record);
    updateProject(currentProject.id, { status: 'building' });

    const startTime = Date.now();
    const artifacts: string[] = [];
    let logIndex = 0;

    for (let i = 0; i < buildSteps.length; i++) {
      const step = buildSteps[i];

      appendBuildLog(`[INFO] 开始 ${step.label}...`);
      await new Promise((resolve) => setTimeout(resolve, step.duration / 2));
      appendBuildLog(`[SUCCESS] ${step.label}完成`);
      logIndex++;

      setBuildProgress(((i + 0.5) / buildSteps.length) * 100);

      if (step.label === '编译源码') {
        artifacts.push('dist/main.js');
        artifacts.push('dist/main.d.ts');
        appendBuildLog(`[INFO] 生成产物: dist/main.js`);
      }
      if (step.label === '打包产物') {
        artifacts.push(`${currentProject.name.toLowerCase().replace(/\s+/g, '-')}.tar.gz`);
        appendBuildLog(`[INFO] 打包完成: ${currentProject.name.toLowerCase().replace(/\s+/g, '-')}.tar.gz`);
      }

      await new Promise((resolve) => setTimeout(resolve, step.duration / 2));
      setBuildProgress(((i + 1) / buildSteps.length) * 100);
    }

    const duration = Date.now() - startTime;

    appendBuildLog(`[SUCCESS] 构建完成! 耗时: ${duration}ms`);

    const finalRecord: BuildRecord = {
      id: buildId,
      projectId: currentProject.id,
      status: 'success',
      logs: `构建成功`,
      duration,
      artifacts,
      timestamp: new Date(),
    };

    updateProject(currentProject.id, {
      status: 'completed',
      buildHistory: [
        ...currentProject.buildHistory.filter((r) => r.id !== buildId),
        finalRecord,
      ],
    });

    setIsBuilding(false);
    setBuildProgress(100);
  };

  if (!currentProject) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-6"
      >
        <div className="flex flex-col items-center justify-center py-20 rounded-2xl bg-gradient-to-br from-[#1a1a2e]/50 to-[#16213e]/50 border border-dashed border-[#00d4ff]/20">
          <FolderKanban className="w-16 h-16 text-[#94a3b8]/30 mb-4" />
          <h3 className="text-lg font-medium text-[#f1f5f9] mb-2">未选择项目</h3>
          <p className="text-sm text-[#94a3b8]">请在左侧选择一个项目以进行构建</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 space-y-6 h-full flex flex-col"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#f1f5f9]">构建中心</h2>
          <p className="text-sm text-[#94a3b8] mt-1">
            当前项目: <span className="text-[#00d4ff]">{currentProject.name}</span>
          </p>
        </div>

        <motion.button
          onClick={simulateBuild}
          disabled={isBuilding}
          className={`px-6 py-3 rounded-xl font-medium flex items-center gap-2 transition-all ${
            isBuilding
              ? 'bg-[#ff6b35]/20 text-[#ff6b35] cursor-not-allowed'
              : 'bg-gradient-to-r from-[#ff6b35] to-[#ff8f5a] text-white shadow-lg shadow-[#ff6b35]/20 hover:shadow-xl hover:shadow-[#ff6b35]/30'
          }`}
          whileHover={!isBuilding ? { scale: 1.02 } : {}}
          whileTap={!isBuilding ? { scale: 0.98 } : {}}
        >
          {isBuilding ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              构建中...
            </>
          ) : (
            <>
              <Hammer className="w-5 h-5" />
              开始构建
            </>
          )}
        </motion.button>
      </div>

      {/* Build Progress */}
      {isBuilding && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-[#1a1a2e]/50 border border-[#ff6b35]/20"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[#f1f5f9]">构建进度</span>
            <span className="text-sm text-[#ff6b35]">{Math.round(buildProgress)}%</span>
          </div>
          <div className="h-2 bg-[#0a0e17] rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-[#ff6b35] to-[#ff8f5a] rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${buildProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <div className="mt-2 flex gap-2">
            {buildSteps.map((step, i) => (
              <span
                key={step.label}
                className={`text-xs px-2 py-1 rounded ${
                  buildProgress > (i / buildSteps.length) * 100
                    ? 'bg-[#10b981]/20 text-[#10b981]'
                    : 'bg-[#0a0e17] text-[#94a3b8]'
                }`}
              >
                {step.label}
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-0">
        <BuildConsole />
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-[#94a3b8] flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            构建历史
          </h3>
          <div className="flex-1 overflow-y-auto">
            <BuildHistory records={currentProject.buildHistory} />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
