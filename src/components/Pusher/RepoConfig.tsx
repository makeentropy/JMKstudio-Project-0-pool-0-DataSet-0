import { useState } from 'react';
import { motion } from 'framer-motion';
import { Github, Server, Loader2 } from 'lucide-react';

interface RepoConfigProps {
  repoUrl: string;
  version: string;
  onRepoUrlChange: (url: string) => void;
  onVersionChange: (version: string) => void;
}

export function RepoConfig({ repoUrl, version, onRepoUrlChange, onVersionChange }: RepoConfigProps) {
  const [isValidating, setIsValidating] = useState(false);
  const [isValid, setIsValid] = useState<boolean | null>(null);

  const validateRepo = async () => {
    if (!repoUrl.trim()) return;
    setIsValidating(true);

    await new Promise((resolve) => setTimeout(resolve, 1000));

    const isValidFormat = repoUrl.match(/^(https?:\/\/)?([\w\-]+\.)+[\w\-]+(\/[\w\-\.]+)*$/);
    setIsValid(!!isValidFormat);
    setIsValidating(false);
  };

  return (
    <div className="space-y-4 p-5 rounded-xl bg-[#0a0e17]/50 border border-[#00d4ff]/10">
      <h4 className="text-sm font-medium text-[#00d4ff]">仓库配置</h4>

      <div>
        <label className="block text-xs text-[#94a3b8] mb-2">仓库地址</label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => {
                onRepoUrlChange(e.target.value);
                setIsValid(null);
              }}
              placeholder="https://registry.example.com/project"
              className="w-full px-4 py-2.5 rounded-lg bg-[#1a1a2e] border border-[#00d4ff]/20 text-[#f1f5f9] placeholder-[#94a3b8]/50 focus:outline-none focus:border-[#00d4ff]/50 transition-all text-sm"
            />
            {isValidating && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#00d4ff] animate-spin" />
            )}
          </div>
          <motion.button
            onClick={validateRepo}
            disabled={!repoUrl.trim() || isValidating}
            className="px-4 py-2.5 rounded-lg bg-[#00d4ff]/10 text-[#00d4ff] border border-[#00d4ff]/30 hover:bg-[#00d4ff]/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            验证
          </motion.button>
        </div>
        {isValid === true && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs text-[#10b981] mt-1"
          >
            仓库地址格式正确
          </motion.p>
        )}
        {isValid === false && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-xs text-[#ef4444] mt-1"
          >
            仓库地址格式无效
          </motion.p>
        )}
      </div>

      <div>
        <label className="block text-xs text-[#94a3b8] mb-2">版本标签</label>
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={version}
              onChange={(e) => onVersionChange(e.target.value)}
              placeholder="v1.0.0"
              className="w-full px-4 py-2.5 rounded-lg bg-[#1a1a2e] border border-[#00d4ff]/20 text-[#f1f5f9] placeholder-[#94a3b8]/50 focus:outline-none focus:border-[#00d4ff]/50 transition-all text-sm"
            />
          </div>
        </div>
        <div className="flex gap-2 mt-2">
          {['v1.0.0', 'v1.1.0', 'v2.0.0'].map((tag) => (
            <button
              key={tag}
              onClick={() => onVersionChange(tag)}
              className={`px-2 py-1 rounded text-xs transition-all ${
                version === tag
                  ? 'bg-[#a855f7]/20 text-[#a855f7] border border-[#a855f7]/30'
                  : 'bg-[#1a1a2e] text-[#94a3b8] border border-[#00d4ff]/10 hover:border-[#00d4ff]/30'
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4 pt-2">
        <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
          <Github className="w-4 h-4" />
          <span>Git</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#94a3b8]">
          <Server className="w-4 h-4" />
          <span>Artifact Registry</span>
        </div>
      </div>
    </div>
  );
}
