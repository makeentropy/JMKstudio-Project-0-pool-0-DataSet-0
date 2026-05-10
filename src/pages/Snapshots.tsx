import { useEffect, useState } from 'react';
import { useAppStore, type Snapshot } from '../store';
import { Plus, Clock, RefreshCcw, Trash2 } from 'lucide-react';

export default function Snapshots() {
  const { snapshots, setSnapshots, addSnapshot, removeSnapshot } = useAppStore();
  const [name, setName] = useState('');
  const [path, setPath] = useState('/mnt/nas');

  useEffect(() => {
    const fetchSnapshots = async () => {
      try {
        const response = await fetch('/api/snapshots');
        const data = await response.json();
        setSnapshots(data);
      } catch (error) {
        console.error('Failed to fetch snapshots:', error);
      }
    };

    fetchSnapshots();
  }, [setSnapshots]);

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/snapshots', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, path }),
      });
      const newSnapshot = await response.json();
      addSnapshot(newSnapshot);
      setName('');
      setPath('/mnt/nas');
    } catch (error) {
      console.error('Failed to create snapshot:', error);
    }
  };

  const handleRestoreSnapshot = async (id: string) => {
    try {
      await fetch(`/api/snapshots/${id}/restore`, { method: 'POST' });
      alert('Snapshot restored successfully');
    } catch (error) {
      console.error('Failed to restore snapshot:', error);
    }
  };

  const handleDeleteSnapshot = async (id: string) => {
    try {
      await fetch(`/api/snapshots/${id}`, { method: 'DELETE' });
      removeSnapshot(id);
    } catch (error) {
      console.error('Failed to delete snapshot:', error);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (date: string): string => {
    return new Date(date).toLocaleString();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-500 to-violet-500 bg-clip-text text-transparent">
            Snapshots
          </h1>
          <p className="text-slate-500 mt-1">
            Manage your mirror snapshots
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100">
        <h2 className="text-xl font-bold text-slate-800 mb-4">Create New Snapshot</h2>
        <form onSubmit={handleCreateSnapshot} className="flex gap-4 flex-wrap">
          <input
            type="text"
            placeholder="Snapshot name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 min-w-[200px] px-4 py-3 rounded-xl border border-slate-200 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all"
            required
          />
          <input
            type="text"
            placeholder="Path"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            className="flex-1 min-w-[200px] px-4 py-3 rounded-xl border border-slate-200 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all"
            required
          />
          <button
            type="submit"
            className="px-6 py-3 bg-sky-600 text-white rounded-xl hover:bg-sky-700 transition-colors font-medium flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Create
          </button>
        </form>
      </div>

      <div className="bg-white rounded-2xl shadow-lg border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Name</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Path</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Size</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Created</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Status</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-slate-700">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {snapshots.map((snapshot: Snapshot) => (
                <tr key={snapshot.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-sky-100 rounded-lg">
                        <Clock className="w-5 h-5 text-sky-600" />
                      </div>
                      <span className="font-medium text-slate-800">{snapshot.name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-slate-600 font-mono text-sm">{snapshot.path}</td>
                  <td className="px-6 py-4 text-slate-700">{formatBytes(snapshot.size)}</td>
                  <td className="px-6 py-4 text-slate-600 text-sm">{formatDate(snapshot.createdAt)}</td>
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      snapshot.status === 'available' ? 'bg-emerald-100 text-emerald-700' :
                      snapshot.status === 'creating' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {snapshot.status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleRestoreSnapshot(snapshot.id)}
                        className="p-2 text-emerald-600 hover:bg-emerald-100 rounded-lg transition-colors"
                        title="Restore"
                      >
                        <RefreshCcw className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteSnapshot(snapshot.id)}
                        className="p-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
