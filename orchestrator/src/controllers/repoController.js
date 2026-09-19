const Repository = require('../models/repository');

exports.createRepo = async (req, res) => {
  try {
    const { repoId, name, sourceUrl, branch } = req.body;
    if (!repoId || !sourceUrl) {
      return res.status(400).json({ error: 'repoId and sourceUrl are required' });
    }
    const existing = await Repository.findOne({ repoId });
    if (existing) {
      return res.status(409).json({ error: 'Repository already exists', repo: existing });
    }
    const repo = await Repository.create({
      repoId,
      name: name || sourceUrl.split('/').pop().replace(/\.git$/, ''),
      sourceUrl,
      branch: branch || 'main',
    });
    res.status(201).json(repo);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.listRepos = async (req, res) => {
  try {
    const repos = await Repository.find().sort({ createdAt: -1 });
    res.json(repos);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.getRepo = async (req, res) => {
  try {
    const repo = await Repository.findOne({ repoId: req.params.id });
    if (!repo) return res.status(404).json({ error: 'Not found' });
    res.json(repo);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

exports.deleteRepo = async (req, res) => {
  try {
    const repo = await Repository.findOneAndDelete({ repoId: req.params.id });
    if (!repo) return res.status(404).json({ error: 'Not found' });
    res.json({ message: 'Deleted', repoId: req.params.id });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};
