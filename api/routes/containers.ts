import express from 'express';
import { randomUUID } from 'crypto';

const router = express.Router();

// Mock data
let containers = [
  {
    id: randomUUID(),
    name: 'nginx-server',
    image: 'nginx:latest',
    status: 'running' as const,
    ports: ['80:80', '443:443'],
    createdAt: new Date('2024-01-10T09:15:00Z').toISOString()
  },
  {
    id: randomUUID(),
    name: 'postgres-db',
    image: 'postgres:15',
    status: 'running' as const,
    ports: ['5432:5432'],
    createdAt: new Date('2024-01-08T16:45:00Z').toISOString()
  }
];

router.get('/', (req, res) => {
  res.json(containers);
});

router.post('/', (req, res) => {
  const { name, image, ports } = req.body;
  const newContainer = {
    id: randomUUID(),
    name,
    image,
    ports: ports || [],
    status: 'created' as const,
    createdAt: new Date().toISOString()
  };
  containers.push(newContainer);
  res.status(201).json(newContainer);
});

router.post('/:id/start', (req, res) => {
  const { id } = req.params;
  const container = containers.find(c => c.id === id);
  if (!container) {
    return res.status(404).json({ error: 'Container not found' });
  }
  container.status = 'running';
  res.status(200).send();
});

router.post('/:id/stop', (req, res) => {
  const { id } = req.params;
  const container = containers.find(c => c.id === id);
  if (!container) {
    return res.status(404).json({ error: 'Container not found' });
  }
  container.status = 'stopped';
  res.status(200).send();
});

router.delete('/:id', (req, res) => {
  const { id } = req.params;
  containers = containers.filter(c => c.id !== id);
  res.status(200).send();
});

export default router;
