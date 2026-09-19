const axios = require('axios');
const neo4j = require('../config/neo4j');

const WORKER_URL = process.env.PYTHON_WORKER_URL || 'http://localhost:8000';

exports.queryRepo = async (req, res) => {
  const { repoId, question } = req.body;
  console.log(`[QUERY] repo=${repoId} question="${question?.substring(0, 80)}"`);

  try {
    if (!repoId || !question) {
      return res.status(400).json({ error: 'repoId and question are required' });
    }
    const workerResp = await axios.post(`${WORKER_URL}/query`, {
      repoId,
      question,
      top_k: req.body.topK || 8,
    });
    res.json(workerResp.data);
  } catch (err) {
    console.error(`[QUERY] Worker failed:`, err.message, err.response?.data);
    res.status(502).json({ error: 'Query failed', details: err.message, worker: err.response?.data });
  }
};

exports.getGraph = async (req, res) => {
  try {
    const { repoId } = req.params;
    const session = neo4j.session();
    const result = await session.run(
      `
      MATCH (n {repo_id: $repoId})
      OPTIONAL MATCH (n)-[r]-(m)
      WHERE m.repo_id = $repoId
      WITH COLLECT(DISTINCT {
        id: elementId(n),
        labels: labels(n),
        name: n.name,
        qualified_name: n.qualified_name,
        path: n.path
      }) AS nodes,
      COLLECT(DISTINCT {
        source: elementId(n),
        target: elementId(m),
        type: type(r)
      }) AS links
      RETURN nodes, links
      `,
      { repoId }
    );
    await session.close();

    if (result.records.length === 0) {
      return res.json({ nodes: [], links: [] });
    }

    const row = result.records[0];
    const nodes = row.get('nodes') || [];
    const links = row.get('links') || [];

    res.json({
      nodes: nodes.filter((n) => n.id),
      links: links.filter((l) => l.source && l.target),
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};
