import { motion } from 'framer-motion';
import { History, CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react';
import type { BuildRecord } from '../../types';

interface BuildHistoryProps {
  records: BuildRecord[];
}

export function BuildHistory({ records }: BuildHistoryProps) {
  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-[#94a3b8]/50">
        <History className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-sm">暂无构建历史</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {[...records].reverse().map((record, index) => (
        <motion.div
          key={record.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
          className="p-4 rounded-xl bg-[#0a0e17]/50 border border-[#00d4ff]/10"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              {record.status === 'success' && (
                <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
              )}
              {record.status === 'failed' && (
                <XCircle className="w-4 h-4 text-[#ef4444]" />
              )}
              {record.status === 'in-progress' && (
                <Loader2 className="w-4 h-4 text-[#ff6b35] animate-spin" />
              )}
              <span className={`text-sm font-medium ${
                record.status === 'success' ? 'text-[#10b981]' :
                record.status === 'failed' ? 'text-[#ef4444]' :
                'text-[#ff6b35]'
              }`}>
                {record.status === 'success' && '构建成功'}
                {record.status === 'failed' && '构建失败'}
                {record.status === 'in-progress' && '构建中'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
              <Clock className="w-3 h-3" />
              <span>{new Date(record.timestamp).toLocaleString('zh-CN')}</span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs text-[#94a3b8]">
            <span>耗时: {record.duration}ms</span>
            <span>产物: {record.artifacts.length} 个</span>
          </div>

          {record.artifacts.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {record.artifacts.map((artifact, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-[#00d4ff]/10 text-[#00d4ff] text-xs"
                >
                  {artifact}
                </span>
              ))}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}
