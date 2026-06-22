import { motion } from 'framer-motion';
import { LayoutDashboard, Plus, Hammer, Upload, Rocket } from 'lucide-react';
import { useProjectStore } from '../../store/projectStore';
import type { ViewType } from '../../types';

const navItems: { id: ViewType; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: '仪表盘', icon: LayoutDashboard },
  { id: 'generator', label: '生成项目', icon: Plus },
  { id: 'builder', label: '构建中心', icon: Hammer },
  { id: 'pusher', label: '推送管理', icon: Upload },
];

export function Navbar() {
  const { activeView, setActiveView } = useProjectStore();

  return (
    <nav className="h-16 bg-[#0a0e17]/90 backdrop-blur-md border-b border-[#00d4ff]/20 flex items-center justify-between px-6 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <motion.div
          className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#00d4ff] to-[#a855f7] flex items-center justify-center"
          whileHover={{ scale: 1.05, rotate: 5 }}
          whileTap={{ scale: 0.95 }}
        >
          <Rocket className="w-6 h-6 text-white" />
        </motion.div>
        <div>
          <h1 className="text-lg font-bold text-[#f1f5f9] tracking-tight">
            DataSci Projecter
          </h1>
          <p className="text-[10px] text-[#94a3b8] uppercase tracking-widest">
            数据科学项目工程管理
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1 bg-[#1a1a2e]/50 rounded-xl p-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeView === item.id;
          return (
            <motion.button
              key={item.id}
              onClick={() => setActiveView(item.id)}
              className={`relative px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                isActive
                  ? 'text-[#00d4ff]'
                  : 'text-[#94a3b8] hover:text-[#f1f5f9]'
              }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNav"
                  className="absolute inset-0 bg-[#00d4ff]/10 rounded-lg border border-[#00d4ff]/30"
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                />
              )}
              <Icon className="w-4 h-4 relative z-10" />
              <span className="text-sm font-medium relative z-10 hidden lg:block">
                {item.label}
              </span>
            </motion.button>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#ff6b35] to-[#ff8f5a] flex items-center justify-center">
          <span className="text-xs font-bold text-white">DS</span>
        </div>
      </div>
    </nav>
  );
}
