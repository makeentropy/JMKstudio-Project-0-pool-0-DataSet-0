import { motion } from 'framer-motion';
import { History, CheckCircle2, XCircle, Clock, Upload } from 'lucide-react';
import type { PushRecord } from '../../types';

interface PushHistoryProps {
  records: PushRecord[];
}

export function PushHistory({ records }: PushHistoryProps) {
  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-[#94a3b8]/50">
        <Upload className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-sm">暂无推送历史</p>
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
          className="p-4 rounded-xl bg-[#0a0e17]/50 border border-[#a855f7]/10"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              {record.status === 'success' && (
                <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
              )}
              {record.status === 'failed' && (
                <XCircle className="w-4 h-4 text-[#ef4444]" />
              )}
              <span className={`text-sm font-medium ${
                record.status === 'success' ? 'text-[#10b981]' : 'text-[#ef4444]'
              }`}>
                {record.status === 'success' ? '推送成功' : '推送失败'}
              </span>
            </div>
            <span className="px-2 py-0.5 rounded bg-[#a855f7]/20 text-[#a855f7] text-xs">
              {record.version}
            </span>
          </div>

          <p className="text-xs text-[#94a3b8] truncate mb-2">{record.targetRepo}</p>

          <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
            <Clock className="w-3 h-3" />
            <span>{new Date(record.timestamp).toLocaleString('zh-CN')}</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
