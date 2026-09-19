require('dotenv').config();
const express = require('express');
const cors = require('cors');
const morgan = require('morgan');
const connectMongoDB = require('./config/db');
const neo4jDriver = require('./config/neo4j');
const repoRoutes = require('./routes/repoRoutes');
const syncRoutes = require('./routes/syncRoutes');
const queryRoutes = require('./routes/queryRoutes');
const browseRoutes = require('./routes/browseRoutes');
const uploadRoutes = require('./routes/uploadRoutes');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors({ origin: ['http://localhost:5173', 'http://127.0.0.1:5173'], credentials: true }));
app.use(express.json());
app.use(morgan('dev'));

(async () => {
  try {
    await connectMongoDB();
  } catch (err) {
    console.error('MongoDB unavailable:', err.message);
  }
  try {
    await neo4jDriver.verifyConnectivity();
    console.log('Neo4j connected');
  } catch (err) {
    console.error('Neo4j unavailable:', err.message);
  }
})();

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'orchestrator', timestamp: new Date().toISOString() });
});

app.use('/api', repoRoutes);
app.use('/api', syncRoutes);
app.use('/api', queryRoutes);
app.use('/api', browseRoutes);
app.use('/api', uploadRoutes);

const server = app.listen(PORT, () => {
  console.log(`Orchestrator running on http://localhost:${PORT}`);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled Rejection:', reason);
});
