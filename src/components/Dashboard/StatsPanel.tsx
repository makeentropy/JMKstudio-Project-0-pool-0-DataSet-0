import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useProjectStore } from '../../store/projectStore';

export function StatsPanel() {
  const { projects } = useProjectStore();

  const statusData = [
    { name: '空闲', value: projects.filter(p => p.status === 'idle').length, color: '#94a3b8' },
    { name: '生成中', value: projects.filter(p => p.status === 'generating').length, color: '#a855f7' },
    { name: '编码中', value: projects.filter(p => p.status === 'coding').length, color: '#00d4ff' },
    { name: '构建中', value: projects.filter(p => p.status === 'building').length, color: '#ff6b35' },
    { name: '已完成', value: projects.filter(p => p.status === 'completed').length, color: '#10b981' },
    { name: '错误', value: projects.filter(p => p.status === 'error').length, color: '#ef4444' },
  ];

  const templateData = [
    { name: '数据集', value: projects.filter(p => p.template === 'dataset-builder').length },
    { name: '模型训练', value: projects.filter(p => p.template === 'model-training').length },
    { name: 'Pipeline', value: projects.filter(p => p.template === 'pipeline').length },
    { name: 'XOR池化', value: projects.filter(p => p.template === 'xor-pool').length },
    { name: '自定义', value: projects.filter(p => p.template === 'custom').length },
  ];

  const totalBuilds = projects.reduce((acc, p) => acc + p.buildHistory.length, 0);
  const successfulBuilds = projects.reduce(
    (acc, p) => acc + p.buildHistory.filter(b => b.status === 'success').length,
    0
  );

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      {/* Summary Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="col-span-3 lg:col-span-1 p-5 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#00d4ff]/20"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-[#94a3b8]">总项目数</h3>
          <div className="w-10 h-10 rounded-xl bg-[#00d4ff]/10 flex items-center justify-center">
            <div className="w-4 h-4 rounded-full bg-[#00d4ff]" />
          </div>
        </div>
        <p className="text-3xl font-bold text-[#f1f5f9]">{projects.length}</p>
        <p className="text-xs text-[#94a3b8] mt-1">
          {projects.filter(p => p.status === 'completed').length} 已完成
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="col-span-3 lg:col-span-1 p-5 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#10b981]/20"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-[#94a3b8]">构建成功率</h3>
          <div className="w-10 h-10 rounded-xl bg-[#10b981]/10 flex items-center justify-center">
            <div className="w-4 h-4 rounded-full bg-[#10b981]" />
          </div>
        </div>
        <p className="text-3xl font-bold text-[#f1f5f9]">
          {totalBuilds > 0 ? Math.round((successfulBuilds / totalBuilds) * 100) : 0}%
        </p>
        <p className="text-xs text-[#94a3b8] mt-1">
          {successfulBuilds} / {totalBuilds} 次成功
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="col-span-3 lg:col-span-1 p-5 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#a855f7]/20"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-[#94a3b8]">总推送次数</h3>
          <div className="w-10 h-10 rounded-xl bg-[#a855f7]/10 flex items-center justify-center">
            <div className="w-4 h-4 rounded-full bg-[#a855f7]" />
          </div>
        </div>
        <p className="text-3xl font-bold text-[#f1f5f9]">
          {projects.reduce((acc, p) => acc + p.pushHistory.length, 0)}
        </p>
        <p className="text-xs text-[#94a3b8] mt-1">活跃项目推送统计</p>
      </motion.div>

      {/* Status Distribution Chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="col-span-3 lg:col-span-2 p-5 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#00d4ff]/20"
      >
        <h3 className="text-sm font-medium text-[#94a3b8] mb-4">项目状态分布</h3>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={statusData}>
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0a0e17',
                  border: '1px solid #00d4ff/30',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* Template Distribution */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="col-span-3 lg:col-span-1 p-5 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#a855f7]/20"
      >
        <h3 className="text-sm font-medium text-[#94a3b8] mb-4">项目类型</h3>
        <div className="space-y-3">
          {templateData.map((item, index) => (
            <div key={item.name} className="flex items-center gap-3">
              <span className="text-xs text-[#94a3b8] w-16">{item.name}</span>
              <div className="flex-1 h-2 bg-[#0a0e17] rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: projects.length > 0 ? `${(item.value / projects.length) * 100}%` : '0%' }}
                  transition={{ delay: 0.5 + index * 0.1, duration: 0.5 }}
                  className="h-full bg-gradient-to-r from-[#00d4ff] to-[#a855f7] rounded-full"
                />
              </div>
              <span className="text-xs text-[#f1f5f9] w-6 text-right">{item.value}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
