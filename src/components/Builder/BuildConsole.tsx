import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Terminal, Trash2 } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';

export function BuildConsole() {
  const { buildLogs, clearBuildLogs } = useProjectStore();
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [buildLogs]);

  return (
    <div className="h-full flex flex-col bg-[#0a0e17] rounded-2xl border border-[#00d4ff]/20 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-[#1a1a2e]/50 border-b border-[#00d4ff]/10">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#00d4ff]" />
          <span className="text-sm font-medium text-[#f1f5f9]">构建日志</span>
          {buildLogs.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-[#00d4ff]/20 text-[#00d4ff] text-xs">
              {buildLogs.length}
            </span>
          )}
        </div>
        {buildLogs.length > 0 && (
          <motion.button
            onClick={clearBuildLogs}
            className="p-1.5 rounded-lg hover:bg-[#ef4444]/10 text-[#94a3b8] hover:text-[#ef4444] transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            <Trash2 className="w-4 h-4" />
          </motion.button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
        {buildLogs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-[#94a3b8]/50">
            <Terminal className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">暂无构建日志</p>
            <p className="text-xs mt-1">开始构建以查看日志输出</p>
          </div>
        ) : (
          <div className="space-y-1">
            {buildLogs.map((log, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.01 }}
                className={`${
                  log.includes('[ERROR]') ? 'text-[#ef4444]' :
                  log.includes('[WARN]') ? 'text-[#ff6b35]' :
                  log.includes('[SUCCESS]') ? 'text-[#10b981]' :
                  log.includes('[INFO]') ? 'text-[#00d4ff]' :
                  'text-[#94a3b8]'
                }`}
              >
                <span className="text-[#94a3b8]/40 mr-2 select-none">
                  {String(index + 1).padStart(4, '0')}
                </span>
                {log}
              </motion.div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}
