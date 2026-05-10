import { useEffect } from 'react';
import { useAppStore } from '../store';
import { Activity, Server, HardDrive, Box } from 'lucide-react';

export default function Dashboard() {
  const { storageStats, setStorageStats } = useAppStore();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/storage');
        const data = await response.json();
        setStorageStats(data);
      } catch (error) {
        console.error('Failed to fetch storage stats:', error);
      }
    };

    fetchStats();
  }, [setStorageStats]);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-500 to-violet-500 bg-clip-text text-transparent">
            NAS Management Dashboard
          </h1>
          <p className="text-slate-500 mt-1">
            Monitor and manage your server
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100 hover:shadow-xl transition-shadow">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-sky-100 rounded-xl">
              <Activity className="w-8 h-8 text-sky-600" />
            </div>
            <span className="text-2xl font-bold text-sky-600">35%</span>
          </div>
          <h3 className="text-slate-500 text-sm mt-4">CPU Usage</h3>
          <p className="text-slate-700 font-medium">4 Cores Active</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100 hover:shadow-xl transition-shadow">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-violet-100 rounded-xl">
              <Server className="w-8 h-8 text-violet-600" />
            </div>
            <span className="text-2xl font-bold text-violet-600">62%</span>
          </div>
          <h3 className="text-slate-500 text-sm mt-4">Memory</h3>
          <p className="text-slate-700 font-medium">6.2 GB / 10 GB</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100 hover:shadow-xl transition-shadow">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-emerald-100 rounded-xl">
              <HardDrive className="w-8 h-8 text-emerald-600" />
            </div>
            <span className="text-2xl font-bold text-emerald-600">45%</span>
          </div>
          <h3 className="text-slate-500 text-sm mt-4">Storage</h3>
          <p className="text-slate-700 font-medium">
            {storageStats ? formatBytes(storageStats.used) : '0 B'} / {storageStats ? formatBytes(storageStats.total) : '0 B'}
          </p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100 hover:shadow-xl transition-shadow">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-orange-100 rounded-xl">
              <Box className="w-8 h-8 text-orange-600" />
            </div>
            <span className="text-2xl font-bold text-orange-600">2</span>
          </div>
          <h3 className="text-slate-500 text-sm mt-4">Containers</h3>
          <p className="text-slate-700 font-medium">Running</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 shadow-lg border border-slate-100">
          <h2 className="text-xl font-bold text-slate-800 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="p-4 bg-sky-50 rounded-xl border-2 border-sky-100 hover:border-sky-300 transition-all hover:bg-sky-100">
              <span className="text-sky-700 font-medium">Create Snapshot</span>
            </button>
            <button className="p-4 bg-violet-50 rounded-xl border-2 border-violet-100 hover:border-violet-300 transition-all hover:bg-violet-100">
              <span className="text-violet-700 font-medium">Compress Data</span>
            </button>
            <button className="p-4 bg-emerald-50 rounded-xl border-2 border-emerald-100 hover:border-emerald-300 transition-all hover:bg-emerald-100">
              <span className="text-emerald-700 font-medium">Start Container</span>
            </button>
            <button className="p-4 bg-orange-50 rounded-xl border-2 border-orange-100 hover:border-orange-300 transition-all hover:bg-orange-100">
              <span className="text-orange-700 font-medium">Encrypt Drive</span>
            </button>
          </div>
        </div>

        <div className="bg-gradient-to-br from-sky-500 to-violet-600 rounded-2xl p-6 shadow-lg">
          <h2 className="text-xl font-bold text-white mb-4">System Status</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between text-white/90">
              <span>Server Status</span>
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
                Online
              </span>
            </div>
            <div className="flex items-center justify-between text-white/90">
              <span>Last Backup</span>
              <span>2 hours ago</span>
            </div>
            <div className="flex items-center justify-between text-white/90">
              <span>Network</span>
              <span>Connected</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
