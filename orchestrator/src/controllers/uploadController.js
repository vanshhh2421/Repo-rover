const fs = require('fs');
const path = require('path');
const axios = require('axios');
const Repository = require('../models/repository');

const WORK_DIR = process.env.WORK_DIR || '.work';
const WORKER_URL = process.env.PYTHON_WORKER_URL || 'http://localhost:8000';

const SUPPORTED_EXTS = new Set([
  '.py', '.js', '.jsx', '.ts', '.tsx',
]);
const SKIP_DIRS = new Set(['node_modules', '.git', '.venv', 'dist', 'build', '__pycache__']);

exports.uploadRepo = async (req, res) => {
  try {
    const { repoId, name, branch } = req.body;
    if (!repoId || !req.files || req.files.length === 0) {
      return res.status(400).json({ error: 'repoId and files are required' });
    }

    const targetDir = path.resolve(WORK_DIR, repoId);
    fs.mkdirSync(targetDir, { recursive: true });

    for (const file of req.files) {
      const relPath = file.originalname;
      if (!relPath) continue;
      const isSkipped = relPath.split(/[/\\]/).slice(0, -1).some((p) => SKIP_DIRS.has(p.toLowerCase()));
      if (isSkipped) { fs.unlinkSync(file.path); continue }
      const ext = path.extname(relPath).toLowerCase();
      if (!SUPPORTED_EXTS.has(ext)) { fs.unlinkSync(file.path); continue }
      const absPath = path.join(targetDir, relPath);
      fs.mkdirSync(path.dirname(absPath), { recursive: true });
      fs.copyFileSync(file.path, absPath);
      fs.unlinkSync(file.path);
    }

    const sourceUrl = targetDir.replace(/\\/g, '/');

    const existing = await Repository.findOne({ repoId });
    if (existing) {
      await Repository.updateOne({ repoId }, { sourceUrl, status: 'not_indexed' });
    } else {
      await Repository.create({
        repoId,
        name: name || repoId,
        sourceUrl,
        branch: branch || 'main',
        status: 'not_indexed',
      });
    }

    await Repository.updateOne({ repoId }, { status: 'indexing' });

    const allFiles = scanFiles(targetDir);
    const relPaths = allFiles.map(f => path.relative(targetDir, f).replace(/\\/g, '/'));

    let workerResponse;
    try {
      workerResponse = await axios.post(`${WORKER_URL}/ingest`, {
        repoId,
        sourceUrl,
        branch: branch || 'main',
        addedOrModifiedFiles: relPaths,
        deletedFiles: [],
      }, { timeout: 0 });
    } catch (err) {
      console.error(`[UPLOAD] Worker failed:`, err.message, err.response?.data);
      await Repository.updateOne({ repoId }, { status: 'error' });
      return res.status(502).json({ error: 'Worker ingestion failed', details: err.message, worker: err.response?.data });
    }

    await Repository.updateOne({ repoId }, {
      status: 'indexed',
      lastSyncAt: new Date(),
      nodeCount: workerResponse.data.symbols_indexed || 0,
    });

    res.json({
      message: 'Upload and sync complete',
      repoId,
      stats: {
        files: workerResponse.data.files_indexed || relPaths.length,
        symbols: workerResponse.data.symbols_indexed || 0,
      },
    });
  } catch (err) {
    console.error(`[UPLOAD] Error:`, err);
    res.status(500).json({ error: err.message });
  }
};

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
