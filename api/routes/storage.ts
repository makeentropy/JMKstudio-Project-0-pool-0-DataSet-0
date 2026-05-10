import express from 'express';

const router = express.Router();

// Mock storage stats
const mockStats = {
  total: 1024 * 1024 * 1024 * 1000, // 1TB
  used: 1024 * 1024 * 1024 * 450,   // 450GB
  available: 1024 * 1024 * 1024 * 550, // 550GB
  compressionRatio: 2.5
};

router.get('/', (req, res) => {
  res.json(mockStats);
});

router.post('/compress', (req, res) => {
  res.json({ success: true });
});

router.post('/encrypt', (req, res) => {
  res.json({ success: true });
});

export default router;
