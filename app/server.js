const express = require('express');
const os = require('os');
const path = require('path');
const { MongoClient } = require('mongodb');

const PORT = process.env.PORT || 3000;
const MONGO_URL = process.env.MONGO_URL; // required, no default on purpose

if (!MONGO_URL) {
  console.error('MONGO_URL environment variable is not set');
  process.exit(1);
}

const POD_NAME = process.env.HOSTNAME || os.hostname();

function getPodIp() {
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      if (net.family === 'IPv4' && !net.internal) return net.address;
    }
  }
  return '127.0.0.1';
}
const POD_IP = getPodIp();

// ---------- MongoDB ----------
const client = new MongoClient(MONGO_URL, { serverSelectionTimeoutMS: 3000 });
let calculations = null; // set once connected

async function connectWithRetry() {
  while (true) {
    try {
      await client.connect();
      const db = client.db(); // db name comes from the connection string
      calculations = db.collection('calculations');
      await calculations.createIndex({ createdAt: -1 });
      console.log('Connected to MongoDB');
      return;
    } catch (err) {
      console.error('MongoDB connection failed, retrying in 3s:', err.message);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
}
connectWithRetry();

// ---------- App ----------
const app = express();
app.use(express.json({ limit: '10kb' }));
app.use(express.static(path.join(__dirname, 'public')));

function parsePositive(value) {
  const n = typeof value === 'string' ? Number(value.trim()) : value;
  return typeof n === 'number' && Number.isFinite(n) && n > 0 ? n : null;
}

function computeEmi(P, annualRate, n) {
  const r = annualRate / 12 / 100;
  const pow = Math.pow(1 + r, n);
  const emi = (P * r * pow) / (pow - 1);
  const totalPayment = emi * n;
  const totalInterest = totalPayment - P;
  const round2 = (x) => Math.round(x * 100) / 100;
  return {
    emi: round2(emi),
    totalPayment: round2(totalPayment),
    totalInterest: round2(totalInterest),
  };
}

// POST /api/emi
app.post('/api/emi', async (req, res) => {
  const body = req.body || {};
  const P = parsePositive(body.P);
  const rate = parsePositive(body.rate);
  const n = parsePositive(body.n);

  const errors = [];
  if (P === null) errors.push('Loan amount must be a positive number');
  if (rate === null) errors.push('Interest rate must be a positive number');
  if (n === null || !Number.isInteger(n)) errors.push('Tenure must be a positive whole number of months');
  if (P !== null && P > 1e12) errors.push('Loan amount is too large');
  if (rate !== null && rate > 100) errors.push('Interest rate must be 100% or less');
  if (n !== null && n > 1200) errors.push('Tenure must be 1200 months or less');
  if (errors.length) return res.status(400).json({ error: errors.join('; ') });

  if (!calculations) return res.status(503).json({ error: 'Database not ready' });

  const result = computeEmi(P, rate, n);

  try {
    await calculations.insertOne({
      principal: P,
      rate,
      months: n,
      emi: result.emi,
      servedBy: POD_NAME,
      createdAt: new Date(),
    });
  } catch (err) {
    console.error('Insert failed:', err.message);
    return res.status(503).json({ error: 'Could not save calculation' });
  }

  res.json({ ...result, servedBy: POD_NAME, podIp: POD_IP });
});

// GET /api/history
app.get('/api/history', async (req, res) => {
  if (!calculations) return res.status(503).json({ error: 'Database not ready' });
  try {
    const rows = await calculations
      .find({}, { projection: { _id: 0 } })
      .sort({ createdAt: -1 })
      .limit(10)
      .toArray();
    res.json(rows);
  } catch (err) {
    console.error('History failed:', err.message);
    res.status(503).json({ error: 'Could not read history' });
  }
});

// GET /health : 200 only if MongoDB is reachable
app.get('/health', async (req, res) => {
  try {
    if (!calculations) throw new Error('not connected');
    await client.db().command({ ping: 1 });
    res.status(200).json({ status: 'ok' });
  } catch (err) {
    res.status(503).json({ status: 'unavailable' });
  }
});

// bad JSON and other errors
app.use((err, req, res, next) => {
  if (err.type === 'entity.parse.failed') return res.status(400).json({ error: 'Invalid JSON' });
  console.error(err);
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, '0.0.0.0', () => console.log(`emi-web listening on ${PORT}, pod ${POD_NAME} (${POD_IP})`));

process.on('SIGTERM', async () => {
  await client.close();
  process.exit(0);
});
