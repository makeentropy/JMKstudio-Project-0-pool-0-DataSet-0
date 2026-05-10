import { useEffect } from 'react';
import { useAppStore } from '../store';
import { HardDrive, Archive, Lock, TrendingUp } from 'lucide-react';

export default function Storage() {
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

  const handleCompress = async () => {
    try {
      const response = await fetch('/api/storage/compress', { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        alert('Compression initiated');
      }
    } catch (error) {
      console.error('Failed to compress:', error);
    }
  };

  const handleEncrypt = async () => {
    try {
      const response = await fetch('/api/storage/encrypt', { method: 'POST' });
      const data = await response.json();
      if (data.success) {
        alert('Encryption initiated');
      }
    } catch (error) {
      console.error('Failed to encrypt:', error);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const usedPercentage = storageStats ? (storageStats.used / storageStats.total) * 100 : 0;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-500 to-violet-500 bg-clip-text text-transparent">
          Storage
        </h1>
        <p className="text-slate-500 mt-1">
          Manage compression and encryption
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 shadow-lg border border-slate-100">
        <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-slate-800">Storage Overview</h2>
            <HardDrive className="w-8 h-8 text-sky-500" />
          </div>

          <div className="mb-6">
            <div className="flex justify-between mb-2">
              <span className="text-slate-600 font-medium">Used Space</span>
              <span className="text-slate-800 font-bold">
                {storageStats ? formatBytes(storageStats.used) : '0 B'} / {storageStats ? formatBytes(storageStats.total) : '0 B'}
              </span>
            </div>
            <div className="h-4 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-sky-500 to-violet-500 rounded-full transition-all duration-500"
                style={{ width: `${usedPercentage}%` }}
              />
            </div>
            <div className="flex justify-between mt-2 text-sm text-slate-500">
              <span>{usedPercentage.toFixed(0)}% used</span>
              <span>{storageStats ? formatBytes(storageStats.available) : '0 B'} available</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-100 rounded-lg">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-emerald-700 font-medium">Compression Ratio</p>
                  <p className="text-2xl font-bold text-emerald-600">
                    {storageStats?.compressionRatio || 0}x
                  </p>
                </div>
              </div>
            </div>

            <div className="p-4 bg-sky-50 rounded-xl border border-sky-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-sky-100 rounded-lg">
                  <Lock className="w-5 h-5 text-sky-600" />
                </div>
                <div>
                  <p className="text-sky-700 font-medium">Encryption</p>
                  <p className="text-2xl font-bold text-sky-600">
                    Active
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100">
            <div className="flex items-center gap-3 mb-4">
              <Archive className="w-6 h-6 text-violet-500" />
              <h2 className="text-xl font-bold text-slate-800">Compress</h2>
            </div>
            <p className="text-slate-600 text-sm mb-4">
              Compress your data to save storage space
            </p>
            <button
              onClick={handleCompress}
              className="w-full py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-700 transition-colors font-medium"
            >
              Start Compression
            </button>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100">
            <div className="flex items-center gap-3 mb-4">
              <Lock className="w-6 h-6 text-emerald-500" />
              <h2 className="text-xl font-bold text-slate-800">Encrypt</h2>
            </div>
            <p className="text-slate-600 text-sm mb-4">
              Encrypt your data for security
            </p>
            <button
              onClick={handleEncrypt}
              className="w-full py-3 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 transition-colors font-medium"
            >
              Encrypt Drive
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
