import { useState } from 'react';
import { motion } from 'framer-motion';
import { Upload, Loader2, FolderKanban, Zap, CheckCircle2, XCircle } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';
import { RepoConfig } from './RepoConfig';
import { PushHistory } from './PushHistory';
import type { PushRecord } from '../../types';

export function ProjectPusher() {
  const { currentProject, addPushRecord, updateProject } = useProjectStore();
  const [repoUrl, setRepoUrl] = useState('https://registry.example.com/datasci-projects');
  const [version, setVersion] = useState('v1.0.0');
  const [isPushing, setIsPushing] = useState(false);
  const [pushStatus, setPushStatus] = useState<'idle' | 'success' | 'failed'>('idle');

  const handlePush = async () => {
    if (!currentProject) return;

    setIsPushing(true);
    setPushStatus('idle');
    updateProject(currentProject.id, { status: 'pushing' });

    await new Promise((resolve) => setTimeout(resolve, 1500));

    const success = Math.random() > 0.2;
    setPushStatus(success ? 'success' : 'failed');

    const record: PushRecord = {
      id: `push_${Date.now()}`,
      projectId: currentProject.id,
      targetRepo: repoUrl,
      version,
      status: success ? 'success' : 'failed',
      timestamp: new Date(),
    };

    addPushRecord(currentProject.id, record);

    if (success) {
      updateProject(currentProject.id, { status: 'completed' });
    } else {
      updateProject(currentProject.id, { status: 'error' });
    }

    setIsPushing(false);
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
          <p className="text-sm text-[#94a3b8]">请在左侧选择一个项目以进行推送</p>
        </div>
      </motion.div>
    );
  }

  const hasBuildArtifacts = currentProject.buildHistory.some(
    (b) => b.status === 'success' && b.artifacts.length > 0
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#f1f5f9]">推送管理</h2>
          <p className="text-sm text-[#94a3b8] mt-1">
            当前项目: <span className="text-[#00d4ff]">{currentProject.name}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <motion.button
            onClick={handlePush}
            disabled={isPushing || !hasBuildArtifacts}
            className={`px-6 py-3 rounded-xl font-medium flex items-center gap-2 transition-all ${
              !hasBuildArtifacts
                ? 'bg-[#94a3b8]/10 text-[#94a3b8] cursor-not-allowed'
                : isPushing
                ? 'bg-[#a855f7]/20 text-[#a855f7] cursor-not-allowed'
                : 'bg-gradient-to-r from-[#a855f7] to-[#c084fc] text-white shadow-lg shadow-[#a855f7]/20 hover:shadow-xl hover:shadow-[#a855f7]/30'
            }`}
            whileHover={hasBuildArtifacts && !isPushing ? { scale: 1.02 } : {}}
            whileTap={hasBuildArtifacts && !isPushing ? { scale: 0.98 } : {}}
          >
            {isPushing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                推送中...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                推送项目
              </>
            )}
          </motion.button>
        </div>
      </div>

      {/* Status Alert */}
      {!hasBuildArtifacts && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-[#ff6b35]/10 border border-[#ff6b35]/30 flex items-center gap-3"
        >
          <Zap className="w-5 h-5 text-[#ff6b35]" />
          <div>
            <p className="text-sm font-medium text-[#ff6b35]">无可推送产物</p>
            <p className="text-xs text-[#ff6b35]/70">请先完成项目构建，再进行推送</p>
          </div>
        </motion.div>
      )}

      {/* Push Result */}
      {pushStatus !== 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-4 rounded-xl border flex items-center gap-3 ${
            pushStatus === 'success'
              ? 'bg-[#10b981]/10 border-[#10b981]/30'
              : 'bg-[#ef4444]/10 border-[#ef4444]/30'
          }`}
        >
          {pushStatus === 'success' ? (
            <>
              <CheckCircle2 className="w-5 h-5 text-[#10b981]" />
              <div>
                <p className="text-sm font-medium text-[#10b981]">推送成功</p>
                <p className="text-xs text-[#10b981]/70">
                  产物已推送到 {repoUrl}
                </p>
              </div>
            </>
          ) : (
            <>
              <XCircle className="w-5 h-5 text-[#ef4444]" />
              <div>
                <p className="text-sm font-medium text-[#ef4444]">推送失败</p>
                <p className="text-xs text-[#ef4444]/70">请检查网络连接和仓库配置</p>
              </div>
            </>
          )}
        </motion.div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RepoConfig
          repoUrl={repoUrl}
          version={version}
          onRepoUrlChange={setRepoUrl}
          onVersionChange={setVersion}
        />

        <div className="space-y-4">
          <h4 className="text-sm font-medium text-[#94a3b8]">推送历史</h4>
          <PushHistory records={currentProject.pushHistory} />
        </div>
      </div>

      {/* Latest Build Artifacts */}
      {hasBuildArtifacts && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="p-5 rounded-xl bg-[#0a0e17]/50 border border-[#00d4ff]/10"
        >
          <h4 className="text-sm font-medium text-[#94a3b8] mb-3">最新构建产物</h4>
          <div className="flex flex-wrap gap-2">
            {currentProject.buildHistory
              .filter((b) => b.status === 'success')
              .slice(-1)[0]
              ?.artifacts.map((artifact, i) => (
                <span
                  key={i}
                  className="px-3 py-1.5 rounded-lg bg-[#00d4ff]/10 text-[#00d4ff] text-sm border border-[#00d4ff]/20"
                >
                  {artifact}
                </span>
              ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
