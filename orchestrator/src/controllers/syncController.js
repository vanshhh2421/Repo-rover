const fs = require('fs');
const path = require('path');
const axios = require('axios');
const Repository = require('../models/repository');

const WORKER_URL = process.env.PYTHON_WORKER_URL || 'http://localhost:8000';

const SUPPORTED_EXTS = new Set([
  '.py', '.js', '.jsx', '.ts', '.tsx',
]);
const SKIP_DIRS = new Set([
  '.work', '.chroma', 'node_modules', '.git', '.venv', 'dist', 'build', '__pycache__',
]);

function scanFiles(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.has(entry.name.toLowerCase())) {
        files.push(...scanFiles(full));
      }
    } else if (SUPPORTED_EXTS.has(path.extname(entry.name).toLowerCase())) {
      files.push(full);
    }
  }
  return files;
}

exports.syncRepo = async (req, res) => {
  const { repoId, sourceUrl, branch } = req.body;
  console.log(`[SYNC] Starting sync for ${repoId} from ${sourceUrl}`);

  try {
    if (!repoId || !sourceUrl) {
      return res.status(400).json({ error: 'repoId and sourceUrl are required' });
    }

    const repoRoot = path.resolve(sourceUrl);
    if (!fs.existsSync(repoRoot)) {
      console.error(`[SYNC] Path not found: ${repoRoot}`);
      return res.status(404).json({ error: 'Repository path not found', path: repoRoot });
    }

    await Repository.updateOne({ repoId }, { status: 'indexing' });

    const allFiles = scanFiles(repoRoot);
    const relPaths = allFiles.map((f) => path.relative(repoRoot, f).replace(/\\/g, '/'));
    console.log(`[SYNC] Found ${relPaths.length} files to ingest`);

    const payload = {
      repoId,
      sourceUrl,
      branch: branch || 'main',
      addedOrModifiedFiles: relPaths,
      deletedFiles: [],
    };

    let workerResponse;
    try {
      console.log(`[SYNC] POST ${WORKER_URL}/ingest`);
      workerResponse = await axios.post(`${WORKER_URL}/ingest`, payload, { timeout: 0 });
      console.log(`[SYNC] Worker response:`, workerResponse.data);
    } catch (err) {
      console.error(`[SYNC] Worker failed:`, err.message, err.response?.data);
      await Repository.updateOne({ repoId }, { status: 'error' });
      return res.status(502).json({ error: 'Worker ingestion failed', details: err.message, worker: err.response?.data });
    }

    await Repository.updateOne(
      { repoId },
      {
        status: 'indexed',
        lastSyncAt: new Date(),
        nodeCount: workerResponse.data.symbols_indexed || 0,
      }
    );

    res.json({
      message: 'Sync complete',
      stats: {
        files: workerResponse.data.files_indexed || relPaths.length,
        symbols: workerResponse.data.symbols_indexed || 0,
      },
    });
  } catch (err) {
    console.error(`[SYNC] Unexpected error:`, err);
    await Repository.updateOne({ repoId: req.body.repoId }, { status: 'error' }).catch(() => {});
    res.status(500).json({ error: err.message });
  }
};
