import express from 'express';
import { randomUUID } from 'crypto';

const router = express.Router();

// Mock data
let snapshots = [
  {
    id: randomUUID(),
    name: 'snapshot-2024-01-15',
    path: '/mnt/nas/snapshots/2024-01-15',
    size: 1024 * 1024 * 512,
    createdAt: new Date('2024-01-15T10:30:00Z').toISOString(),
    status: 'available' as const
  },
  {
    id: randomUUID(),
    name: 'snapshot-2024-01-10',
    path: '/mnt/nas/snapshots/2024-01-10',
    size: 1024 * 1024 * 768,
    createdAt: new Date('2024-01-10T14:20:00Z').toISOString(),
    status: 'available' as const
  }
];

router.get('/', (req, res) => {
  res.json(snapshots);
});

router.post('/', (req, res) => {
  const { name, path } = req.body;
  const newSnapshot = {
    id: randomUUID(),
    name,
    path,
    size: Math.floor(Math.random() * 1024 * 1024 * 1024),
    createdAt: new Date().toISOString(),
    status: 'available' as const
  };
  snapshots.push(newSnapshot);
  res.status(201).json(newSnapshot);
});

router.post('/:id/restore', (req, res) => {
  const { id } = req.params;
  const snapshot = snapshots.find(s => s.id === id);
  if (!snapshot) {
    return res.status(404).json({ error: 'Snapshot not found' });
  }
  res.status(200).send();
});

router.delete('/:id', (req, res) => {
  const { id } = req.params;
  snapshots = snapshots.filter(s => s.id !== id);
  res.status(200).send();
});

export default router;
