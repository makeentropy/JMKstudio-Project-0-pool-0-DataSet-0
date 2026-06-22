import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Loader2, ArrowRight, Settings } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';
import { templates, createProject } from '../../utils/mockData';
import { TemplateMarket } from './TemplateMarket';
import type { ProjectTemplate, DriverConfig } from '../../types';

export function ProjectGenerator() {
  const [selectedTemplate, setSelectedTemplate] = useState<ProjectTemplate | null>(null);
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [driverType, setDriverType] = useState<'xor-pool' | 'base-xor'>('xor-pool');
  const [poolSize, setPoolSize] = useState(1024);
  const [redundancyLevel, setRedundancyLevel] = useState(3);
  const [isGenerating, setIsGenerating] = useState(false);

  const { addProject, setActiveView, setCurrentProject } = useProjectStore();

  const handleGenerate = async () => {
    if (!selectedTemplate || !projectName.trim()) return;

    setIsGenerating(true);

    const driverConfig: DriverConfig | undefined =
      selectedTemplate === 'xor-pool' || selectedTemplate === 'dataset-builder'
        ? { type: driverType, poolSize, redundancyLevel }
        : undefined;

    await new Promise((resolve) => setTimeout(resolve, 2000));

    const newProject = createProject(
      projectName.trim(),
      projectDescription.trim() || templates.find((t) => t.id === selectedTemplate)?.description || '',
      selectedTemplate,
      driverConfig
    );

    addProject(newProject);
    setCurrentProject(newProject);
    setIsGenerating(false);
    setActiveView('dashboard');
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="p-6 space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#f1f5f9]">项目生成器</h2>
          <p className="text-sm text-[#94a3b8] mt-1">选择模板，快速初始化数据科学项目</p>
        </div>
      </div>

      {/* Template Selection */}
      <div className="mb-8">
        <h3 className="text-lg font-semibold text-[#f1f5f9] mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-[#00d4ff]" />
          选择项目模板
        </h3>
        <TemplateMarket
          selectedTemplate={selectedTemplate}
          onSelectTemplate={setSelectedTemplate}
          templates={templates}
        />
      </div>

      {/* Project Configuration */}
      {selectedTemplate && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="p-6 rounded-2xl bg-gradient-to-br from-[#1a1a2e] to-[#16213e] border border-[#00d4ff]/20 space-y-6"
        >
          <h3 className="text-lg font-semibold text-[#f1f5f9] flex items-center gap-2">
            <Settings className="w-5 h-5 text-[#a855f7]" />
            项目配置
          </h3>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#94a3b8] mb-2">
                  项目名称 <span className="text-[#ef4444]">*</span>
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="输入项目名称"
                  className="w-full px-4 py-3 rounded-xl bg-[#0a0e17] border border-[#00d4ff]/20 text-[#f1f5f9] placeholder-[#94a3b8]/50 focus:outline-none focus:border-[#00d4ff]/50 focus:ring-2 focus:ring-[#00d4ff]/20 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#94a3b8] mb-2">
                  项目描述
                </label>
                <textarea
                  value={projectDescription}
                  onChange={(e) => setProjectDescription(e.target.value)}
                  placeholder="描述项目用途和目标..."
                  rows={3}
                  className="w-full px-4 py-3 rounded-xl bg-[#0a0e17] border border-[#00d4ff]/20 text-[#f1f5f9] placeholder-[#94a3b8]/50 focus:outline-none focus:border-[#00d4ff]/50 focus:ring-2 focus:ring-[#00d4ff]/20 transition-all resize-none"
                />
              </div>
            </div>

            {/* Driver Configuration for XOR Pool */}
            {(selectedTemplate === 'xor-pool' || selectedTemplate === 'dataset-builder') && (
              <div className="space-y-4 p-4 rounded-xl bg-[#0a0e17]/50 border border-[#00d4ff]/10">
                <h4 className="text-sm font-medium text-[#00d4ff]">驱动层配置</h4>

                <div>
                  <label className="block text-xs text-[#94a3b8] mb-2">驱动类型</label>
                  <div className="flex gap-2">
                    {(['xor-pool', 'base-xor'] as const).map((type) => (
                      <button
                        key={type}
                        onClick={() => setDriverType(type)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          driverType === type
                            ? 'bg-[#00d4ff]/20 text-[#00d4ff] border border-[#00d4ff]/50'
                            : 'bg-[#1a1a2e] text-[#94a3b8] border border-[#00d4ff]/10 hover:border-[#00d4ff]/30'
                        }`}
                      >
                        {type === 'xor-pool' ? 'XOR Pool' : 'Base XOR'}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-[#94a3b8] mb-2">
                      池大小 (MB): {poolSize}
                    </label>
                    <input
                      type="range"
                      min={256}
                      max={4096}
                      step={256}
                      value={poolSize}
                      onChange={(e) => setPoolSize(Number(e.target.value))}
                      className="w-full accent-[#00d4ff]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-[#94a3b8] mb-2">
                      冗余级别: {redundancyLevel}
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={5}
                      value={redundancyLevel}
                      onChange={(e) => setRedundancyLevel(Number(e.target.value))}
                      className="w-full accent-[#ff6b35]"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Generate Button */}
          <div className="flex justify-end pt-4">
            <motion.button
              onClick={handleGenerate}
              disabled={!projectName.trim() || isGenerating}
              className={`px-8 py-3 rounded-xl font-medium flex items-center gap-2 transition-all ${
                projectName.trim() && !isGenerating
                  ? 'bg-gradient-to-r from-[#00d4ff] to-[#a855f7] text-white shadow-lg shadow-[#00d4ff]/20 hover:shadow-xl hover:shadow-[#00d4ff]/30'
                  : 'bg-[#1a1a2e] text-[#94a3b8] cursor-not-allowed'
              }`}
              whileHover={projectName.trim() && !isGenerating ? { scale: 1.02 } : {}}
              whileTap={projectName.trim() && !isGenerating ? { scale: 0.98 } : {}}
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  生成项目
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </motion.button>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
