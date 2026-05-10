import { useEffect, useState } from 'react';
import { useAppStore, type Container } from '../store';
import { Plus, Box, Play, Square, Trash2 } from 'lucide-react';

export default function Containers() {
  const { containers, setContainers } = useAppStore();
  const [name, setName] = useState('');
  const [image, setImage] = useState('');
  const [ports, setPorts] = useState('');

  useEffect(() => {
    const fetchContainers = async () => {
      try {
        const response = await fetch('/api/containers');
        const data = await response.json();
        setContainers(data);
      } catch (error) {
        console.error('Failed to fetch containers:', error);
      }
    };

    fetchContainers();
  }, [setContainers]);

  const handleCreateContainer = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/containers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          image,
          ports: ports.split(',').map(p => p.trim()),
        }),
      });
      const newContainer = await response.json();
      setContainers([...containers, newContainer]);
      setName('');
      setImage('');
      setPorts('');
    } catch (error) {
      console.error('Failed to create container:', error);
    }
  };

  const handleStartContainer = async (id: string) => {
    try {
      await fetch(`/api/containers/${id}/start`, { method: 'POST' });
      setContainers(containers.map(c =>
        c.id === id ? { ...c, status: 'running' } : c
      ));
    } catch (error) {
      console.error('Failed to start container:', error);
    }
  };

  const handleStopContainer = async (id: string) => {
    try {
      await fetch(`/api/containers/${id}/stop`, { method: 'POST' });
      setContainers(containers.map(c =>
        c.id === id ? { ...c, status: 'stopped' } : c
      ));
    } catch (error) {
      console.error('Failed to stop container:', error);
    }
  };

  const handleDeleteContainer = async (id: string) => {
    try {
      await fetch(`/api/containers/${id}`, { method: 'DELETE' });
      setContainers(containers.filter(c => c.id !== id));
    } catch (error) {
      console.error('Failed to delete container:', error);
    }
  };

  const formatDate = (date: string): string => {
    return new Date(date).toLocaleString();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-500 to-violet-500 bg-clip-text text-transparent">
            Containers
          </h1>
          <p className="text-slate-500 mt-1">
            Manage your virtual containers
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100">
        <h2 className="text-xl font-bold text-slate-800 mb-4">Create New Container</h2>
        <form onSubmit={handleCreateContainer} className="flex gap-4 flex-wrap">
          <input
            type="text"
            placeholder="Container name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 min-w-[150px] px-4 py-3 rounded-xl border border-slate-200 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all"
            required
          />
          <input
            type="text"
            placeholder="Image (e.g., nginx:latest)"
            value={image}
            onChange={(e) => setImage(e.target.value)}
            className="flex-1 min-w-[200px] px-4 py-3 rounded-xl border border-slate-200 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all"
            required
          />
          <input
            type="text"
            placeholder="Ports (e.g., 80:80, 443:443)"
            value={ports}
            onChange={(e) => setPorts(e.target.value)}
            className="flex-1 min-w-[150px] px-4 py-3 rounded-xl border border-slate-200 focus:border-sky-500 focus:ring-2 focus:ring-sky-200 outline-none transition-all"
          />
          <button
            type="submit"
            className="px-6 py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-700 transition-colors font-medium flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Create
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {containers.map((container: Container) => (
          <div
            key={container.id}
            className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100 hover:shadow-xl transition-all"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-orange-100 rounded-xl">
                  <Box className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">{container.name}</h3>
                  <p className="text-sm text-slate-500">{container.image}</p>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                container.status === 'running' ? 'bg-emerald-100 text-emerald-700' :
                container.status === 'stopped' ? 'bg-slate-100 text-slate-700' :
                'bg-blue-100 text-blue-700'
              }`}>
                {container.status}
              </span>
            </div>

            {container.ports.length > 0 && (
              <div className="mb-4">
                <p className="text-xs text-slate-500 mb-1">Ports</p>
                <div className="flex flex-wrap gap-2">
                  {container.ports.map((port, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded-lg font-mono"
                    >
                      {port}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="text-xs text-slate-500 mb-4">
              Created: {formatDate(container.createdAt)}
            </div>

            <div className="flex gap-2">
              {container.status !== 'running' && (
                <button
                  onClick={() => handleStartContainer(container.id)}
                  className="flex-1 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
                >
                  <Play className="w-4 h-4" />
                  Start
                </button>
              )}
              {container.status === 'running' && (
                <button
                  onClick={() => handleStopContainer(container.id)}
                  className="flex-1 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors flex items-center justify-center gap-2 text-sm font-medium"
                >
                  <Square className="w-4 h-4" />
                  Stop
                </button>
              )}
              <button
                onClick={() => handleDeleteContainer(container.id)}
                className="p-2 text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                title="Delete"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
