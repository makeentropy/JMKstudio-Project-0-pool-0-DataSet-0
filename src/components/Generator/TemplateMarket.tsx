import { motion } from 'framer-motion';
import { Database, Brain, GitBranch, HardDrive, Sparkles, Check } from 'lucide-react';
import type { Template, ProjectTemplate } from '../../types';

const iconMap: Record<string, typeof Database> = {
  'dataset-builder': Database,
  'model-training': Brain,
  'pipeline': GitBranch,
  'xor-pool': HardDrive,
  'custom': Sparkles,
};

interface TemplateMarketProps {
  selectedTemplate: ProjectTemplate | null;
  onSelectTemplate: (template: ProjectTemplate) => void;
  templates: Template[];
}

export function TemplateMarket({ selectedTemplate, onSelectTemplate, templates }: TemplateMarketProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {templates.map((template, index) => {
        const Icon = iconMap[template.id] || Sparkles;
        const isSelected = selectedTemplate === template.id;

        return (
          <motion.div
            key={template.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            onClick={() => onSelectTemplate(template.id)}
            className={`relative p-5 rounded-2xl border cursor-pointer transition-all duration-300 ${
              isSelected
                ? 'bg-[#00d4ff]/10 border-[#00d4ff]/50 shadow-[0_0_30px_rgba(0,212,255,0.2)]'
                : 'bg-[#1a1a2e]/50 border-[#00d4ff]/10 hover:border-[#00d4ff]/30 hover:bg-[#1a1a2e]'
            }`}
            whileHover={{ scale: 1.02, y: -4 }}
            whileTap={{ scale: 0.98 }}
          >
            {isSelected && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute top-3 right-3 w-6 h-6 rounded-full bg-[#00d4ff] flex items-center justify-center"
              >
                <Check className="w-4 h-4 text-[#0a0e17]" />
              </motion.div>
            )}

            <div className={`w-14 h-14 rounded-xl mb-4 flex items-center justify-center ${
              isSelected
                ? 'bg-gradient-to-br from-[#00d4ff]/20 to-[#a855f7]/20'
                : 'bg-[#0a0e17]'
            }`}>
              <Icon className={`w-7 h-7 ${
                isSelected ? 'text-[#00d4ff]' : 'text-[#94a3b8]'
              }`} />
            </div>

            <h3 className="text-base font-bold text-[#f1f5f9] mb-2">{template.name}</h3>
            <p className="text-xs text-[#94a3b8] mb-4 leading-relaxed">{template.description}</p>

            <div className="flex flex-wrap gap-2">
              {template.features.map((feature) => (
                <span
                  key={feature}
                  className={`text-[10px] px-2 py-1 rounded-full ${
                    isSelected
                      ? 'bg-[#00d4ff]/20 text-[#00d4ff]'
                      : 'bg-[#0a0e17] text-[#94a3b8]'
                  }`}
                >
                  {feature}
                </span>
              ))}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
